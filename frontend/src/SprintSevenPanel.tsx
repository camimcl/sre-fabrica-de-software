import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from './api'

type Strategy = 'FIXED' | 'RULES' | 'AI_HYBRID'
type Status = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED'

type Dashboard = {
  totals: { executions: number; scenarios: number; endpoints: number; comparisons: number }
  executions_by_status: Record<string, number>
  executions_by_strategy: Record<string, number>
  completion_rate: number
  performance: { avg_throughput_rps: number; avg_latency_p95_ms: number; avg_error_rate: number }
  timeseries_executions_per_day: { day: string; count: number }[]
}

type ExecutionRow = {
  id: string
  scenario_id: string
  status: Status
  strategy: Strategy
  started_at: string | null
  ended_at: string | null
  created_at: string
}
type ExecutionPage = { items: ExecutionRow[]; total: number; page: number; page_size: number }

type OperationLog = {
  id: string
  actor_id: string
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'EXECUTE'
  entity_type: string
  entity_id: string | null
  summary: string | null
  created_at: string
}
type OperationLogPage = { items: OperationLog[]; total: number; page: number; page_size: number }

type Tab = 'dashboard' | 'queries' | 'operations'
type Props = { token: string; projectId: string; isQa: boolean; report: (message: unknown) => void }

const strategyLabel: Record<Strategy, string> = { FIXED: 'Fixa', RULES: 'Regras', AI_HYBRID: 'IA híbrida' }
const statuses: Status[] = ['PENDING', 'RUNNING', 'COMPLETED', 'CANCELLED', 'FAILED']
const strategies: Strategy[] = ['FIXED', 'RULES', 'AI_HYBRID']

async function download(path: string, token: string, filename: string) {
  const response = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error(`Falha na exportação (${response.status})`)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function BarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <div className="s7-bars">
      {data.map((d) => (
        <div className="s7-bar-row" key={d.label}>
          <span className="s7-bar-label">{d.label}</span>
          <div className="s7-bar-track"><div className="s7-bar-fill" style={{ width: `${(d.value / max) * 100}%` }} /></div>
          <span className="s7-bar-value">{d.value}</span>
        </div>
      ))}
    </div>
  )
}

function Sparkline({ points }: { points: { day: string; count: number }[] }) {
  if (points.length === 0) return <p className="empty compact">Sem execuções no período.</p>
  const max = Math.max(1, ...points.map((p) => p.count))
  const width = 320
  const height = 80
  const step = points.length > 1 ? width / (points.length - 1) : 0
  const coords = points.map((p, i) => `${i * step},${height - (p.count / max) * height}`).join(' ')
  return (
    <svg className="s7-spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Execuções por dia">
      <polyline fill="none" stroke="currentColor" strokeWidth="2" points={coords} />
    </svg>
  )
}

export default function SprintSevenPanel({ token, projectId, isQa, report }: Props) {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [execPage, setExecPage] = useState<ExecutionPage | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'' | Status>('')
  const [strategyFilter, setStrategyFilter] = useState<'' | Strategy>('')
  const [page, setPage] = useState(1)

  const [logs, setLogs] = useState<OperationLogPage | null>(null)
  const [logPage, setLogPage] = useState(1)
  const [expanded, setExpanded] = useState<string | null>(null)

  const requestRef = useRef(0)

  const queryString = useCallback((extra: Record<string, string>) => {
    const params = new URLSearchParams(extra)
    if (dateFrom) params.set('date_from', `${dateFrom}T00:00:00`)
    if (dateTo) params.set('date_to', `${dateTo}T23:59:59`)
    return params.toString()
  }, [dateFrom, dateTo])

  const loadDashboard = useCallback(async () => {
    const request = ++requestRef.current
    setLoading(true)
    try {
      const qs = queryString({})
      const data = await api<Dashboard>(`/projects/${projectId}/dashboard${qs ? `?${qs}` : ''}`, 'GET', undefined, token)
      if (request === requestRef.current) setDashboard(data)
    } catch (error) { report(error) } finally { if (request === requestRef.current) setLoading(false) }
  }, [projectId, token, queryString, report])

  const loadExecutions = useCallback(async () => {
    const request = ++requestRef.current
    try {
      const extra: Record<string, string> = { page: String(page), page_size: '10' }
      if (search.trim()) extra.search = search.trim()
      if (statusFilter) extra.status = statusFilter
      if (strategyFilter) extra.strategy = strategyFilter
      const data = await api<ExecutionPage>(`/projects/${projectId}/executions?${queryString(extra)}`, 'GET', undefined, token)
      if (request === requestRef.current) setExecPage(data)
    } catch (error) { report(error) }
  }, [projectId, token, queryString, page, search, statusFilter, strategyFilter, report])

  const loadLogs = useCallback(async () => {
    if (!isQa) return
    const request = ++requestRef.current
    try {
      const data = await api<OperationLogPage>(`/audit/logs?${queryString({ page: String(logPage), page_size: '10' })}`, 'GET', undefined, token)
      if (request === requestRef.current) setLogs(data)
    } catch (error) { report(error) }
  }, [token, logPage, isQa, queryString, report])

  useEffect(() => { if (tab === 'dashboard') void loadDashboard() }, [tab, loadDashboard])
  useEffect(() => { if (tab === 'queries') void loadExecutions() }, [tab, loadExecutions])
  useEffect(() => { if (tab === 'operations') void loadLogs() }, [tab, loadLogs])

  const totalPages = execPage ? Math.max(1, Math.ceil(execPage.total / execPage.page_size)) : 1
  const logTotalPages = logs ? Math.max(1, Math.ceil(logs.total / logs.page_size)) : 1

  return (
    <section className="card reports-card s7-panel">
      <div className="section-heading sprint-heading">
        <div>
          <span className="eyebrow">Sprint 07 · consulta e acompanhamento</span>
          <h2>Dashboard, consultas e auditoria</h2>
          <p className="muted">Indicadores reais, pesquisa com filtros, exportação e histórico de operações.</p>
        </div>
      </div>

      <div className="filter-row" role="tablist" aria-label="Seções da Sprint 07">
        <button role="tab" aria-selected={tab === 'dashboard'} className={tab === 'dashboard' ? 'active' : ''} onClick={() => setTab('dashboard')}>Dashboard</button>
        <button role="tab" aria-selected={tab === 'queries'} className={tab === 'queries' ? 'active' : ''} onClick={() => setTab('queries')}>Consultas</button>
        {isQa && <button role="tab" aria-selected={tab === 'operations'} className={tab === 'operations' ? 'active' : ''} onClick={() => setTab('operations')}>Operações</button>}
      </div>

      <div className="s7-period">
        <label>De<input type="date" value={dateFrom} onChange={(e) => { setPage(1); setLogPage(1); setDateFrom(e.target.value) }} /></label>
        <label>Até<input type="date" value={dateTo} onChange={(e) => { setPage(1); setLogPage(1); setDateTo(e.target.value) }} /></label>
      </div>

      {tab === 'dashboard' && (loading && !dashboard ? <p className="empty compact">Carregando indicadores…</p> : dashboard && (
        <div className="s7-dashboard">
          <div className="s7-kpis">
            <article><span>Execuções</span><strong>{dashboard.totals.executions}</strong></article>
            <article><span>Cenários</span><strong>{dashboard.totals.scenarios}</strong></article>
            <article><span>Endpoints</span><strong>{dashboard.totals.endpoints}</strong></article>
            <article><span>Comparações</span><strong>{dashboard.totals.comparisons}</strong></article>
            <article><span>Conclusão</span><strong>{(dashboard.completion_rate * 100).toFixed(0)}%</strong></article>
            <article><span>Throughput médio</span><strong>{dashboard.performance.avg_throughput_rps.toFixed(1)} rps</strong></article>
            <article><span>P95 médio</span><strong>{dashboard.performance.avg_latency_p95_ms.toFixed(0)} ms</strong></article>
            <article><span>Erro médio</span><strong>{(dashboard.performance.avg_error_rate * 100).toFixed(1)}%</strong></article>
          </div>
          <div className="s7-charts">
            <div><h3>Execuções por status</h3><BarChart data={statuses.map((s) => ({ label: s, value: dashboard.executions_by_status[s] ?? 0 }))} /></div>
            <div><h3>Execuções por estratégia</h3><BarChart data={strategies.map((s) => ({ label: strategyLabel[s], value: dashboard.executions_by_strategy[s] ?? 0 }))} /></div>
            <div className="s7-timeseries"><h3>Execuções por dia</h3><Sparkline points={dashboard.timeseries_executions_per_day} /></div>
          </div>
        </div>
      ))}

      {tab === 'queries' && (
        <div className="s7-queries">
          <div className="s7-controls">
            <input placeholder="Buscar por cenário" value={search} onChange={(e) => { setPage(1); setSearch(e.target.value) }} />
            <select value={statusFilter} onChange={(e) => { setPage(1); setStatusFilter(e.target.value as Status | '') }}><option value="">Status (todos)</option>{statuses.map((s) => <option key={s} value={s}>{s}</option>)}</select>
            <select value={strategyFilter} onChange={(e) => { setPage(1); setStrategyFilter(e.target.value as Strategy | '') }}><option value="">Estratégia (todas)</option>{strategies.map((s) => <option key={s} value={s}>{strategyLabel[s]}</option>)}</select>
            <button onClick={() => void loadExecutions()}>Aplicar</button>
            <button onClick={() => download(`/projects/${projectId}/exports/executions.csv?${queryString({ ...(search.trim() ? { search: search.trim() } : {}), ...(statusFilter ? { status: statusFilter } : {}), ...(strategyFilter ? { strategy: strategyFilter } : {}) })}`, token, 'executions.csv').catch(report)}>Exportar CSV</button>
          </div>
          <div className="history-list">
            {execPage?.items.map((row) => (
              <article key={row.id} className="history-item">
                <span><strong>{row.strategy}</strong><small>{row.status} · {row.id.slice(0, 8)} · {new Date(row.created_at).toLocaleString('pt-BR')}</small></span>
                <button onClick={() => download(`/projects/${projectId}/scenarios/${row.scenario_id}/executions/${row.id}/report.pdf`, token, `execution-${row.id.slice(0, 8)}.pdf`).catch(report)}>PDF</button>
              </article>
            ))}
            {execPage && execPage.items.length === 0 && <p className="empty compact">Nenhuma execução para os filtros aplicados.</p>}
          </div>
          <div className="s7-pager">
            <button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Anterior</button>
            <span>Página {execPage?.page ?? 1} de {totalPages} · {execPage?.total ?? 0} registros</span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Próxima</button>
          </div>
        </div>
      )}

      {tab === 'operations' && isQa && (
        <div className="s7-operations">
          <div className="history-list">
            {logs?.items.map((entry) => (
              <article key={entry.id} className="history-item s7-log">
                <button className="s7-log-head" onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}>
                  <strong>{entry.action} · {entry.entity_type}</strong>
                  <small>{new Date(entry.created_at).toLocaleString('pt-BR')} · {entry.entity_id?.slice(0, 8) ?? '—'}</small>
                </button>
                {expanded === entry.id && entry.summary && <pre className="s7-log-summary">{JSON.stringify(JSON.parse(entry.summary), null, 2)}</pre>}
              </article>
            ))}
            {logs && logs.items.length === 0 && <p className="empty compact">Nenhuma operação registrada.</p>}
          </div>
          <div className="s7-pager">
            <button disabled={logPage <= 1} onClick={() => setLogPage((p) => Math.max(1, p - 1))}>Anterior</button>
            <span>Página {logs?.page ?? 1} de {logTotalPages} · {logs?.total ?? 0} registros</span>
            <button disabled={logPage >= logTotalPages} onClick={() => setLogPage((p) => p + 1)}>Próxima</button>
          </div>
        </div>
      )}
    </section>
  )
}
