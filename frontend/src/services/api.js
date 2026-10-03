const BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')

export async function request(path, { method = 'GET', body, signal } = {}) {
  let response
  try {
    response = await fetch(`${BASE}${path}`, {
      method, signal,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Não foi possível conectar ao backend. Confira se o FastAPI está rodando na porta 8000.')
  }
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.detail
    const message = Array.isArray(detail)
      ? detail.map(e => `${e.loc?.slice(1).join('.') || 'Campo'}: ${e.msg}`).join(' · ')
      : typeof detail === 'string' ? detail : `A operação falhou (${response.status}).`
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return data
}

// Percorre as páginas para não esconder registros após o limite do backend.
export async function listAll(path, signal) {
  const items = []
  for (let offset = 0; ; offset += 100) {
    const batch = await request(`${path}${path.includes('?') ? '&' : '?'}limite=100&offset=${offset}`, { signal })
    items.push(...batch)
    if (batch.length < 100) return items
  }
}
export const userPath = id => `/usuarios/${id}`

export async function fetchPdf(uid, id) {
  let response
  try { response=await fetch(`${BASE}${userPath(uid)}/curriculos/${id}/pdf`) }
  catch { throw new Error('Não foi possível conectar ao backend para gerar o PDF.') }
  if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(typeof data?.detail==='string'?data.detail:`Falha ao gerar PDF (${response.status}).`)}
  if(!response.headers.get('content-type')?.includes('application/pdf'))throw new Error('O servidor não retornou um PDF válido.')
  return response.blob()
}
