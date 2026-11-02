/** Calendar filters use the user's local day, including its final millisecond. */
export function periodQuery(dateFrom: string, dateTo: string, extra: Record<string, string> = {}) {
  const params = new URLSearchParams(extra)
  if (dateFrom) params.set('date_from', new Date(`${dateFrom}T00:00:00.000`).toISOString())
  if (dateTo) params.set('date_to', new Date(`${dateTo}T23:59:59.999`).toISOString())
  return params.toString()
}

export function readableSummary(summary: string | null) {
  if (!summary) return 'Sem detalhes adicionais.'
  try { return JSON.stringify(JSON.parse(summary), null, 2) } catch { return summary }
}
