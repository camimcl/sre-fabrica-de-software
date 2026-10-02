import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'

import { api } from './api'

type EndpointOption = {
  id: string
  name: string
  authorization_confirmed: boolean
}
type Scenario = {
  id: string
  name: string
  endpoint_id: string
  duration_seconds: number
  initial_concurrency: number
  max_concurrency: number
  ramp_up_per_window: number
  strategy: 'FIXED' | 'RULES' | 'AI_HYBRID'
  p95_limit_ms: number
  error_rate_limit: string
}
type Execution = {
  id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED'
  strategy: Scenario['strategy']
  model_version_id: string | null
  started_at: string | null
  ended_at: string | null
}
type Metric = {
  id: string
  sequence_number: number
  concurrency: number
  throughput_rps: string
  latency_p95_ms: string
  error_rate: string
}
type Prediction = {
  id: string
  metric_window_id: string
  risk_probability: string
  predicted_degradation: boolean
  inference_latency_ms: number
}
type Decision = {
  id: string
  metric_window_id: string
  strategy: 'RULES' | 'AI_HYBRID'
  action: 'INCREASE' | 'HOLD' | 'DECREASE' | 'STOP'
  previous_concurrency: number
  next_concurrency: number
  reason: string
}
type ModelVersion = {
  id: string
  version: string
  algorithm: string
  status: 'CANDIDATE' | 'APPROVED' | 'RETIRED'
  f1_score: string | null
  recall_score: string | null
  accuracy_score: string | null
  training_sample_count: number
}
type ScenarioForm = {
  name: string
  endpoint_id: string
  duration_seconds: number
  initial_concurrency: number
  max_concurrency: number
  ramp_up_per_window: number
  timeout_ms: number
  strategy: Scenario['strategy']
  p95_limit_ms: number
  error_rate_limit: string
}

const emptyForm: ScenarioForm = {
  name: 'Teste adaptativo',
  endpoint_id: '',
  duration_seconds: 30,
  initial_concurrency: 2,
  max_concurrency: 20,
  ramp_up_per_window: 2,
  timeout_ms: 3000,
  strategy: 'AI_HYBRID',
  p95_limit_ms: 800,
  error_rate_limit: '0.05000',
}

type Props = {
  token: string
  projectId: string
  endpoints: EndpointOption[]
  canEdit: boolean
  isQa: boolean
  report: (message: unknown) => void
}

export default function SprintFivePanel({
  token,
  projectId,
  endpoints,
  canEdit,
  isQa,
  report,
}: Props) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [scenarioId, setScenarioId] = useState('')
  const [executions, setExecutions] = useState<Execution[]>([])
  const [executionId, setExecutionId] = useState('')
  const [metrics, setMetrics] = useState<Metric[]>([])
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [models, setModels] = useState<ModelVersion[]>([])
  const [form, setForm] = useState<ScenarioForm>(emptyForm)
  const [busy, setBusy] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const authorizedEndpointId = endpoints.find((endpoint) => endpoint.authorization_confirmed)?.id ?? ''

  const selectedExecution = executions.find((row) => row.id === executionId)
  const approvedModel = models.find((model) => model.status === 'APPROVED')
  const predictionByWindow = useMemo(
    () => new Map(predictions.map((prediction) => [prediction.metric_window_id, prediction])),
    [predictions],
  )
  const decisionByWindow = useMemo(
    () => new Map(decisions.map((decision) => [decision.metric_window_id, decision])),
    [decisions],
  )

  const refreshScenarios = useCallback(async () => {
    const rows = await api<Scenario[]>(`/projects/${projectId}/scenarios`, 'GET', undefined, token)
    setScenarios(rows)
    setScenarioId((current) => (rows.some((row) => row.id === current) ? current : rows[0]?.id ?? ''))
  }, [projectId, token])

  const refreshModels = useCallback(async () => {
    setModels(await api<ModelVersion[]>('/intelligence/models', 'GET', undefined, token))
  }, [token])

  const refreshExecutions = useCallback(async () => {
    if (!scenarioId) {
      setExecutions([])
      return
    }
    const rows = await api<Execution[]>(
      `/projects/${projectId}/scenarios/${scenarioId}/executions`,
      'GET',
      undefined,
      token,
    )
    setExecutions(rows)
    setExecutionId((current) =>
      rows.some((row) => row.id === current) ? current : rows.at(-1)?.id ?? '',
    )
  }, [projectId, scenarioId, token])

  const refreshMonitor = useCallback(async () => {
    if (!scenarioId || !executionId) {
      setMetrics([])
      setPredictions([])
      setDecisions([])
      return
    }
    const base = `/projects/${projectId}/scenarios/${scenarioId}/executions/${executionId}`
    const [execution, windows, risks, controls] = await Promise.all([
      api<Execution>(base, 'GET', undefined, token),
      api<Metric[]>(`${base}/metric-windows`, 'GET', undefined, token),
      api<Prediction[]>(`${base}/risk-predictions`, 'GET', undefined, token),
      api<Decision[]>(`${base}/control-decisions`, 'GET', undefined, token),
    ])
    setExecutions((current) => current.map((row) => (row.id === execution.id ? execution : row)))
    setMetrics(windows)
    setPredictions(risks)
    setDecisions(controls)
  }, [executionId, projectId, scenarioId, token])

  useEffect(() => {
    setForm((current) => ({ ...current, endpoint_id: authorizedEndpointId }))
  }, [authorizedEndpointId])

  useEffect(() => {
    Promise.all([refreshScenarios(), refreshModels()]).catch(report)
  }, [projectId, refreshModels, refreshScenarios, report])

  useEffect(() => {
    setExecutionId('')
    setMetrics([])
    setPredictions([])
    setDecisions([])
    setAcknowledged(false)
    refreshExecutions().catch(report)
  }, [refreshExecutions, report])

  useEffect(() => {
    refreshMonitor().catch(report)
    if (selectedExecution?.status !== 'RUNNING') return
    const timer = window.setInterval(() => refreshMonitor().catch(report), 2000)
    return () => window.clearInterval(timer)
  }, [refreshMonitor, report, selectedExecution?.status])

  async function createScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy('scenario')
    try {
      const saved = await api<Scenario>(
        `/projects/${projectId}/scenarios`,
        'POST',
        form,
        token,
      )
      await refreshScenarios()
      setScenarioId(saved.id)
      report('Cenário persistido e pronto para execução.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  async function createAndStartExecution() {
    if (!scenarioId || !acknowledged) return
    setBusy('execution')
    try {
      const created = await api<Execution>(
        `/projects/${projectId}/scenarios/${scenarioId}/executions`,
        'POST',
        { authorization_acknowledged: true },
        token,
      )
      setExecutionId(created.id)
      await api<Execution>(
        `/projects/${projectId}/scenarios/${scenarioId}/executions/${created.id}/start`,
        'POST',
        undefined,
        token,
      )
      await refreshExecutions()
      setExecutionId(created.id)
      report('Execução iniciada. O monitor será atualizado automaticamente.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  async function stopExecution() {
    if (!scenarioId || !executionId) return
    setBusy('stop')
    try {
      await api<Execution>(
        `/projects/${projectId}/scenarios/${scenarioId}/executions/${executionId}/cancel`,
        'POST',
        { cancellation_reason: 'Parada emergencial solicitada pela interface' },
        token,
      )
      await refreshMonitor()
      report('Parada emergencial registrada.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  async function trainModel() {
    setBusy('train')
    try {
      await api<ModelVersion>('/intelligence/models/train', 'POST', undefined, token)
      await refreshModels()
      report('Treinamento concluído; a nova versão está como candidata.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  async function approveModel(modelId: string) {
    setBusy(modelId)
    try {
      await api<ModelVersion>(`/intelligence/models/${modelId}/approve`, 'POST', undefined, token)
      await refreshModels()
      report('Modelo aprovado para as próximas execuções híbridas.')
    } catch (error) {
      report(error)
    } finally {
      setBusy('')
    }
  }

  return (
    <section className="card sprint-five-card">
      <div className="section-heading sprint-heading">
        <div>
          <span className="eyebrow">Sprint 05 · segundo módulo</span>
          <h2>Inteligência e controle adaptativo</h2>
          <p className="muted">Fluxo real: cenário → execução → métricas → risco → decisão → nova concorrência.</p>
        </div>
        <span className={approvedModel ? 'model-ready' : 'model-fallback'}>
          {approvedModel ? `IA aprovada · ${approvedModel.algorithm}` : 'Fallback por regras ativo'}
        </span>
      </div>

      <div className="adaptive-grid">
        <div className="adaptive-column">
          <div className="subsection-heading"><h3>Cenários</h3><span>{scenarios.length}</span></div>
          {scenarios.length ? (
            <select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}>
              {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name} · {scenario.strategy}</option>)}
            </select>
          ) : <p className="empty compact">Nenhum cenário persistido neste projeto.</p>}
          {canEdit && (
            <form className="stack compact-form" onSubmit={createScenario}>
              <label>Nome<input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
              <label>Endpoint autorizado<select required value={form.endpoint_id} onChange={(event) => setForm({ ...form, endpoint_id: event.target.value })}><option value="">Selecione</option>{endpoints.filter((endpoint) => endpoint.authorization_confirmed).map((endpoint) => <option key={endpoint.id} value={endpoint.id}>{endpoint.name}</option>)}</select></label>
              <div className="form-row triple">
                <label>Duração (s)<input type="number" min={1} max={3600} value={form.duration_seconds} onChange={(event) => setForm({ ...form, duration_seconds: Number(event.target.value) })} /></label>
                <label>Inicial<input type="number" min={1} max={500} value={form.initial_concurrency} onChange={(event) => setForm({ ...form, initial_concurrency: Number(event.target.value) })} /></label>
                <label>Máxima<input type="number" min={1} max={500} value={form.max_concurrency} onChange={(event) => setForm({ ...form, max_concurrency: Number(event.target.value) })} /></label>
              </div>
              <div className="form-row triple">
                <label>Ajuste<input type="number" min={0} max={500} value={form.ramp_up_per_window} onChange={(event) => setForm({ ...form, ramp_up_per_window: Number(event.target.value) })} /></label>
                <label>P95 limite<input type="number" min={1} max={300000} value={form.p95_limit_ms} onChange={(event) => setForm({ ...form, p95_limit_ms: Number(event.target.value) })} /></label>
                <label>Erro limite<input type="number" min={0} max={1} step="0.01" value={form.error_rate_limit} onChange={(event) => setForm({ ...form, error_rate_limit: event.target.value })} /></label>
              </div>
              <label>Estratégia<select value={form.strategy} onChange={(event) => setForm({ ...form, strategy: event.target.value as Scenario['strategy'] })}><option value="AI_HYBRID">IA híbrida</option><option value="RULES">Regras</option><option value="FIXED">Fixa</option></select></label>
              <button className="primary" disabled={!form.endpoint_id || busy === 'scenario'} type="submit">Salvar cenário</button>
            </form>
          )}
        </div>

        <div className="adaptive-column">
          <div className="subsection-heading"><h3>Execuções</h3><span>{executions.length}</span></div>
          {executions.length ? <select value={executionId} onChange={(event) => setExecutionId(event.target.value)}>{executions.map((execution) => <option key={execution.id} value={execution.id}>{execution.status} · {execution.strategy} · {execution.id.slice(0, 8)}</option>)}</select> : <p className="empty compact">Crie e inicie a primeira execução.</p>}
          {canEdit && <><label className="checkbox"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /> Confirmo que tenho autorização para testar este alvo.</label><div className="actions adaptive-actions"><button className="primary" disabled={!scenarioId || !acknowledged || busy === 'execution'} onClick={createAndStartExecution}>Criar e iniciar</button><button className="danger" disabled={selectedExecution?.status !== 'RUNNING' || busy === 'stop'} onClick={stopExecution}>Parada emergencial</button></div></>}
          {selectedExecution && <div className="execution-status"><strong>{selectedExecution.status}</strong><span>{selectedExecution.model_version_id ? 'Modelo local associado' : selectedExecution.strategy === 'AI_HYBRID' ? 'Executando com fallback quando necessário' : 'Controle sem modelo'}</span></div>}
        </div>

        <div className="adaptive-column">
          <div className="subsection-heading"><h3>Modelos locais</h3><span>{models.length}</span></div>
          {models.length ? <div className="model-list">{models.map((model) => <article key={model.id}><div><strong>{model.algorithm}</strong><small>{model.version} · {model.training_sample_count} amostras</small><small>F1 {model.f1_score ?? '—'} · recall {model.recall_score ?? '—'} · acurácia {model.accuracy_score ?? '—'}</small></div><span className={`model-status ${model.status.toLowerCase()}`}>{model.status}</span>{isQa && model.status === 'CANDIDATE' && <button disabled={busy === model.id} onClick={() => approveModel(model.id)}>Aprovar</button>}</article>)}</div> : <p className="empty compact">Ainda não há versão treinada.</p>}
          {isQa && <button className="primary train-button" disabled={busy === 'train'} onClick={trainModel}>Treinar nova versão</button>}
          <p className="helper">O treinamento exige ao menos 20 amostras temporais e as duas classes de resultado.</p>
        </div>
      </div>

      <div className="monitor-block">
        <div className="subsection-heading"><h3>Monitor adaptativo</h3><span>{metrics.length} janelas</span></div>
        {metrics.length ? <div className="table-scroll"><table><thead><tr><th>Janela</th><th>Concorrência</th><th>Throughput</th><th>P95</th><th>Erros</th><th>Risco</th><th>Decisão</th></tr></thead><tbody>{metrics.map((metric) => { const risk = predictionByWindow.get(metric.id); const decision = decisionByWindow.get(metric.id); return <tr key={metric.id}><td>#{metric.sequence_number + 1}</td><td>{metric.concurrency}</td><td>{Number(metric.throughput_rps).toFixed(1)} rps</td><td>{Number(metric.latency_p95_ms).toFixed(0)} ms</td><td>{(Number(metric.error_rate) * 100).toFixed(1)}%</td><td>{risk ? `${(Number(risk.risk_probability) * 100).toFixed(0)}%` : 'regras'}</td><td>{decision ? <span title={decision.reason}>{decision.action} · {decision.previous_concurrency}→{decision.next_concurrency}</span> : '—'}</td></tr> })}</tbody></table></div> : <p className="empty compact">As janelas, previsões e decisões aparecerão após o início da execução.</p>}
      </div>
    </section>
  )
}
