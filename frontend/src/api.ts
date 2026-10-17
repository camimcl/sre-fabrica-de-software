export async function api<T>(
  path: string,
  method = 'GET',
  body?: unknown,
  token?: string,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const detail = data.detail
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!item || typeof item !== 'object') return null
          const field = Array.isArray(item.loc) ? item.loc.at(-1) : null
          const message = typeof item.msg === 'string' ? item.msg : null
          return message ? `${field ? `${field}: ` : ''}${message}` : null
        })
        .filter(Boolean)
      throw new Error(messages.length ? messages.join(' · ') : `Falha na operação (${response.status})`)
    }
    throw new Error(
      typeof detail === 'string' ? detail : `Falha na operação (${response.status})`,
    )
  }
  return response.status === 204 ? (undefined as T) : (await response.json()) as T
}
