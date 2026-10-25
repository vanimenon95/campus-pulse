// One small fetch wrapper: adds the JWT, parses JSON, throws Error(message) on failure.
const BASE = import.meta.env.VITE_API_URL || '/api'
let token = localStorage.getItem('cp_token') || null

export const setToken = (t) => {
  token = t
  t ? localStorage.setItem('cp_token', t) : localStorage.removeItem('cp_token')
}
export const getToken = () => token

async function request(method, path, body) {
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('Cannot reach the server. Is the backend running?')
  }
  const raw = await res.text()
  let data = {}
  try { data = JSON.parse(raw) } catch { /* not JSON */ }
  if (!res.ok && !data.error && raw.trimStart().startsWith('<')) {
    const e = new Error('The API was not found at ' + BASE + '. Deploy the backend and set VITE_API_URL (see README), or serve the site from Flask.')
    e.status = res.status
    throw e
  }
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, b = {}) => request('POST', p, b),
  put: (p, b = {}) => request('PUT', p, b),
  del: (p) => request('DELETE', p),
}
