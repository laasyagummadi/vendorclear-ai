// API base resolution:
// 1. window.API_BASE — manual override for split deployments (frontend on a CDN, backend elsewhere)
// 2. production build — same origin: the backend serves this SPA, so relative URLs just work
// 3. dev (vite on :3000) — the backend runs separately on :8000
const API_BASE =
  (typeof window !== 'undefined' && window.API_BASE) ||
  (import.meta.env.PROD ? '' : 'http://localhost:8000')
const API = API_BASE + '/api/v1'

let _token = localStorage.getItem('vc_token') || ''
let _refresh = localStorage.getItem('vc_refresh') || ''
let _onUnauth = null
let _refreshing = null   // in-flight refresh promise, shared across concurrent 401s

export function setToken(t) {
  _token = t
  if (t) localStorage.setItem('vc_token', t); else localStorage.removeItem('vc_token')
}
export function setRefreshToken(t) {
  _refresh = t
  if (t) localStorage.setItem('vc_refresh', t); else localStorage.removeItem('vc_refresh')
}
export function getToken() { return _token }
export function setUnauthHandler(fn) { _onUnauth = fn }

// Attempt to exchange the refresh token for a new access token.
// Returns true on success. Concurrent callers share one in-flight request.
async function tryRefresh() {
  if (!_refresh) return false
  if (_refreshing) return _refreshing
  _refreshing = (async () => {
    try {
      const res = await fetch(API + '/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: _refresh }),
      })
      if (!res.ok) return false
      const data = await res.json()
      if (data?.access_token) {
        setToken(data.access_token)
        if (data.refresh_token) setRefreshToken(data.refresh_token)
        return true
      }
      return false
    } catch {
      return false
    } finally {
      _refreshing = null
    }
  })()
  return _refreshing
}

export async function api(method, path, body = null, isForm = false, _retried = false) {
  const headers = {}
  const hadToken = !!_token
  if (_token) headers['Authorization'] = 'Bearer ' + _token
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const opts = { method, headers }
  if (body) opts.body = isForm ? body : JSON.stringify(body)
  try {
    const res = await fetch(API + path, opts)

    // 401/403 on a request that carried a token means the access token is
    // expired or invalid. Before treating it as a dead session, try once to
    // silently refresh using the refresh token, then replay the request.
    // (Public auth endpoints carry no token, so a 401 there is a real
    // credential error and is surfaced to the caller unchanged.)
    if ((res.status === 401 || res.status === 403) && hadToken && !_retried) {
      const refreshed = await tryRefresh()
      if (refreshed) {
        return api(method, path, body, isForm, true)   // replay once
      }
      setRefreshToken('')
      if (_onUnauth) _onUnauth()
      return null
    }
    if ((res.status === 401 || res.status === 403) && hadToken) {
      setRefreshToken('')
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
