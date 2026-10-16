import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { api } from './api'

type Strategy = 'FIXED' | 'RULES' | 'AI_HYBRID'
type ExecutionReport = {
  id: string
  execution_id: string
  total_requests: number
  successful_requests: number
  average_throughput_rps: string
  final_latency_p95_ms: string
  final_error_rate: string
  summary: string | null
  generated_at: string
}
type HistoryItem = {
  execution_id: string
  scenario_id: string
  scenario_name: string
  strategy: Strategy
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED'
  started_at: string | null
  ended_at: string | null
  report: ExecutionReport | null
}
type MetricStats = {
  mean: number
  standard_deviation: number
  minimum: number
  maximum: number
}
type StrategyResult = {
  runs: number
  throughput_rps: MetricStats
  latency_p95_ms: MetricStats
  error_rate: MetricStats
  total_requests: number
  successful_requests: number
  timeouts: number
  peak_concurrency: number
  compliance_rate: MetricStats
}
type Comparison = {
  id: string
  name: string
  repetitions_per_strategy: number
  conditions_fingerprint: string
  conditions: Record<string, unknown>
  results: Record<string, StrategyResult | Record<string, unknown>>
  conclusion: string
  execution_ids: string[]
  generated_at: string
}

const strategies: Strategy[] = ['FIXED', 'RULES', 'AI_HYBRID']
const strategyLabel: Record<Strategy, string> = {
  FIXED: 'Fixa',
  RULES: 'Regras',
  AI_HYBRID: 'IA híbrida',
}

type Props = {
  token: string
  projectId: string
  canEdit: boolean
  report: (message: unknown) => void
}

export default function SprintSixReportsPanel({ token, projectId, canEdit, report }: Props) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [comparisons, setComparisons] = useState<Comparison[]>([])
  const [selectedComparisonId, setSelectedComparisonId] = useState('')
  const [selectedExecutions, setSelectedExecutions] = useState<string[]>([])
  const [comparisonName, setComparisonName] = useState('Comparação controlada Sprint 06')
  const [strategyFilter, setStrategyFilter] = useState<'ALL' | Strategy>('ALL')
  const [busy, setBusy] = useState('')
  const refreshRequest = useRef(0)

  const refresh = useCallback(async () => {
    const request = ++refreshRequest.current
    const [executionRows, comparisonRows] = await Promise.all([
      api<HistoryItem[]>(`/projects/${projectId}/reports/executions`, 'GET', undefined, token),
      api<Comparison[]>(`/projects/${projectId}/reports/comparisons`, 'GET', undefined, token),
    ])
    if (request !== refreshRequest.current) return
    setHistory(executionRows)
    setComparisons(comparisonRows)
    setSelectedComparisonId((current) =>
      comparisonRows.some((row) => row.id === current) ? current : comparisonRows[0]?.id ?? '',
    )
  }, [projectId, token])

  useEffect(() => {
    setHistory([])
    setComparisons([])
    setSelectedComparisonId('')
    setSelectedExecutions([])
    void refresh().catch(report)
    return () => { refreshRequest.current += 1 }
  }, [refresh, report])

  const selectedComparison = comparisons.find((row) => row.id === selectedComparisonId)
  const selectedExecutionSet = useMemo(() => new Set(selectedExecutions), [selectedExecutions])
  const visibleHistory = useMemo(
    () => strategyFilter === 'ALL'
      ? history
      : history.filter((item) => item.strategy === strategyFilter),
    [history, strategyFilter],
  )
  const selectedCounts = useMemo(() => {
    const result: Record<Strategy, number> = { FIXED: 0, RULES: 0, AI_HYBRID: 0 }
    for (const item of history) {
      if (item.status === 'COMPLETED' && selectedExecutionSet.has(item.execution_id)) {
        result[item.strategy] += 1
      }
    }
    return result
  }, [history, selectedExecutionSet])
  const counts = Object.values(selectedCounts)
  const comparisonReady = counts.every((count) => count >= 3) && new Set(counts).size === 1

  function toggleExecution(executionId: string) {
    setSelectedExecutions((current) => current.includes(executionId)
      ? current.filter((id) => id !== executionId)
      : [...current, executionId])
  }

  async function generateReport(item: HistoryItem) {
    setBusy(item.execution_id)
    try {
      await api<ExecutionReport>(
        `/projects/${projectId}/scenarios/${item.scenario_id}/executions/${item.execution_id}/report`,
        'POST',
        undefined,
        token,
      )
      await refresh()
      report('Relatório da execução gerado e persistido.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  async function createComparison() {
    if (!comparisonReady) return
    setBusy('comparison')
    try {
      const saved = await api<Comparison>(
        `/projects/${projectId}/reports/comparisons`,
        'POST',
        { name: comparisonName, execution_ids: selectedExecutions },
        token,
      )
      await refresh()
      setSelectedComparisonId(saved.id)
      setSelectedExecutions([])
      report('Comparação persistida com condições equivalentes e repetições balanceadas.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  return (
    <section className="card reports-card">
      <div className="section-heading sprint-heading">
        <div>
          <span className="eyebrow">Sprint 06 · terceiro módulo</span>
          <h2>Histórico e avaliação experimental</h2>
          <p className="muted">Compare estratégias somente com condições equivalentes e ao menos três repetições por estratégia.</p>
        </div>
        <span className="evidence-pill">{comparisons.length} comparações persistidas</span>
      </div>

      <div className="report-layout">
        <div className="report-history">
          <div className="subsection-heading"><h3>Execuções do projeto</h3><span>{history.length}</span></div>
          <div className="filter-row" role="group" aria-label="Filtrar histórico por estratégia">
            {(['ALL', ...strategies] as const).map((strategy) => <button type="button" aria-pressed={strategyFilter === strategy} key={strategy} className={strategyFilter === strategy ? 'active' : ''} onClick={() => setStrategyFilter(strategy)}>{strategy === 'ALL' ? 'Todas' : strategyLabel[strategy]}</button>)}
          </div>
          <div className="history-list">
            {visibleHistory.map((item) => <article key={item.execution_id} className="history-item">
              <label className="run-selector">
                <input type="checkbox" disabled={!canEdit || item.status !== 'COMPLETED'} checked={selectedExecutionSet.has(item.execution_id)} onChange={() => toggleExecution(item.execution_id)} />
                <span><strong>{item.scenario_name}</strong><small>{strategyLabel[item.strategy]} · {item.status} · {item.execution_id.slice(0, 8)}</small></span>
              </label>
              <div className="run-result">{item.report ? <><strong>{Number(item.report.average_throughput_rps).toFixed(1)} rps</strong><small>P95 final {Number(item.report.final_latency_p95_ms).toFixed(0)} ms · erro {(Number(item.report.final_error_rate) * 100).toFixed(1)}%</small></> : canEdit && ['COMPLETED', 'CANCELLED', 'FAILED'].includes(item.status) ? <button disabled={busy === item.execution_id} onClick={() => generateReport(item)}>Gerar relatório</button> : <small>Sem relatório</small>}</div>
            </article>)}
            {!visibleHistory.length && <p className="empty compact">Nenhuma execução encontrada para este filtro.</p>}
          </div>
        </div>

        <aside className="experiment-builder">
          <div className="subsection-heading"><h3>Nova comparação</h3><span>{selectedExecutions.length} selecionadas</span></div>
          <div className="strategy-counts">{strategies.map((strategy) => <div key={strategy}><span>{strategyLabel[strategy]}</span><strong>{selectedCounts[strategy]}</strong><small>mínimo 3</small></div>)}</div>
          <label>Nome da evidência<input maxLength={120} value={comparisonName} onChange={(event) => setComparisonName(event.target.value)} /></label>
          <p className={comparisonReady ? 'comparison-ready' : 'comparison-guidance'}>{comparisonReady ? 'Amostra balanceada. O backend ainda validará todas as condições.' : 'Selecione a mesma quantidade de execuções concluídas para as três estratégias.'}</p>
          {canEdit && <button className="primary" disabled={!comparisonReady || !comparisonName.trim() || busy === 'comparison'} onClick={createComparison}>Gerar comparação</button>}
        </aside>
      </div>

      <div className="comparison-block">
        <div className="subsection-heading"><h3>Resultados comparativos</h3>{comparisons.length > 0 && <select aria-label="Comparação selecionada" value={selectedComparisonId} onChange={(event) => setSelectedComparisonId(event.target.value)}>{comparisons.map((comparison) => <option key={comparison.id} value={comparison.id}>{comparison.name}</option>)}</select>}</div>
        {selectedComparison ? <>
          <div className="comparison-meta"><span>{selectedComparison.repetitions_per_strategy} repetições por estratégia</span><span>Condições #{selectedComparison.conditions_fingerprint.slice(0, 10)}</span><span>{new Date(selectedComparison.generated_at).toLocaleString('pt-BR')}</span></div>
          <div className="strategy-results">{strategies.map((strategy) => { const result = selectedComparison.results[strategy] as StrategyResult; return <article key={strategy}><span>{strategyLabel[strategy]}</span><strong>{result.throughput_rps.mean.toFixed(1)} rps</strong><small>± {result.throughput_rps.standard_deviation.toFixed(1)} · P95 {result.latency_p95_ms.mean.toFixed(0)} ms</small><small>Erro {(result.error_rate.mean * 100).toFixed(2)}% · conformidade {(result.compliance_rate.mean * 100).toFixed(1)}%</small></article> })}</div>
          <p className="comparison-conclusion">{selectedComparison.conclusion}</p>
        </> : <p className="empty compact">Nenhuma comparação foi gerada. Selecione execuções equivalentes no histórico.</p>}
      </div>
    </section>
  )
}
