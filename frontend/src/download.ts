/** Authenticated downloads shared by consultations and comparison reports. */
export async function download(path: string, token: string, filename: string) {
  const response = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const detail = typeof data?.detail === 'string' ? data.detail : `Falha na exportação (${response.status})`
    throw new Error(detail === 'Execution report not found'
      ? 'Este relatório ainda não foi gerado. Solicite ao QA proprietário que o gere na área Relatórios.'
      : detail)
  }
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  try {
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(url)
  }
}
