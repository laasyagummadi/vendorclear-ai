// API base resolution:
// 1. window.API_BASE — manual override for split deployments (frontend on a CDN, backend elsewhere)
// 2. production build — same origin: the backend serves this SPA, so relative URLs just work
// 3. dev (vite on :3000) — the backend runs separately on :8000
const API_BASE =
  (typeof window !== 'undefined' && window.API_BASE) ||
  (import.meta.env.PROD ? '' : 'http://localhost:8000')
const API = API_BASE + '/api/v1'

let _token = localStorage.getItem('vc_token') || ''
let _onUnauth = null

export function setToken(t) { _token = t; if (t) localStorage.setItem('vc_token', t); else localStorage.removeItem('vc_token') }
export function getToken() { return _token }
export function setUnauthHandler(fn) { _onUnauth = fn }

export async function api(method, path, body = null, isForm = false) {
  const headers = {}
  const hadToken = !!_token
  if (_token) headers['Authorization'] = 'Bearer ' + _token
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const opts = { method, headers }
  if (body) opts.body = isForm ? body : JSON.stringify(body)
  try {
    const res = await fetch(API + path, opts)
    // Only treat 401/403 as "your session died" when this request actually
    // carried a token. Public auth endpoints (login/register) also return
    // 401 for plain wrong-credentials, which is a different situation and
    // must surface its real error message to the caller, not be swallowed
    // and misreported as a session expiry.
    if ((res.status === 401 || res.status === 403) && hadToken) {
      if (_onUnauth) _onUnauth()
      return null
    }
    const ct = res.headers.get('content-type') || ''
    const data = ct.includes('application/json') ? await res.json() : await res.text()
    if (!res.ok) throw { status: res.status, data }
    return data
  } catch (e) {
    if (e.status) throw e
    throw { status: 0, data: { detail: 'Network error — is the backend running?' } }
  }
}
