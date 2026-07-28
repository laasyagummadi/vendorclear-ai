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

// For requests that can't go through api() (e.g. file downloads where the
// response isn't JSON) — build the full URL and auth header directly.
export function apiUrl(path) { return API + path }
export function authHeaders() {
  return _token ? { Authorization: `Bearer ${_token}` } : {}
}

// Authenticated binary/file download (CSV export, etc). Mirrors api()'s
// 401-handling: an expired access token is silently refreshed and the
// request retried once, instead of just failing. Returns a Blob on
// success; throws { status, message } on failure so callers can show
// the user *something* rather than the download quietly doing nothing.
export async function apiDownload(path, _retried = false) {
  const hadToken = !!_token
  let res
  try {
    res = await fetch(API + path, { headers: authHeaders() })
  } catch {
    throw { status: 0, message: 'Network error — is the backend running?' }
  }

  if (res.status === 401 && hadToken && !_retried) {
    const refreshed = await tryRefresh()
    if (refreshed) return apiDownload(path, true)   // replay once
    setRefreshToken('')
    if (_onUnauth) _onUnauth()
    throw { status: res.status, message: 'Your session expired — please log in again.' }
  }
  if (!res.ok) {
    let detail = ''
    try { detail = (await res.json())?.detail || '' } catch { /* not JSON */ }
    throw { status: res.status, message: detail || `Export failed (HTTP ${res.status})` }
  }
  return res.blob()
}


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

export async function api(method, path, body = null, isForm = false, _retried = false, timeoutMs = null) {
  const headers = {}
  const hadToken = !!_token
  if (_token) headers['Authorization'] = 'Bearer ' + _token
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const opts = { method, headers }
  if (body) opts.body = isForm ? body : JSON.stringify(body)

  const controller = timeoutMs ? new AbortController() : null
  if (controller) opts.signal = controller.signal
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null

  try {
    const res = await fetch(API + path, opts)

    // A 401 means the access token itself is expired/invalid — worth a
    // silent refresh-and-retry, then a forced logout if that fails.
    // A 403 means the token is VALID but the user's role isn't permitted
    // for this specific action (e.g. RBAC-gated endpoints) — that's not a
    // dead session, so it must NOT log the user out. Conflating the two
    // used to silently sign people out (and swallow the real "you don't
    // have permission to do this" message) any time they hit a role-gated
    // endpoint they weren't allowed to use.
    if (res.status === 401 && hadToken && !_retried) {
      const refreshed = await tryRefresh()
      if (refreshed) {
        return api(method, path, body, isForm, true, timeoutMs)   // replay once
      }
      setRefreshToken('')
      if (_onUnauth) _onUnauth()
      return null
    }
    if (res.status === 401 && hadToken) {
      setRefreshToken('')
      if (_onUnauth) _onUnauth()
      return null
    }

    const ct = res.headers.get('content-type') || ''
    const data = ct.includes('application/json') ? await res.json() : await res.text()
    if (!res.ok) throw { status: res.status, data }
    return data
  } catch (e) {
    if (e.name === 'AbortError') {
      throw { status: 0, data: { detail: 'Request timed out — the server took too long to respond (if this is an email/SMTP action, double-check your SMTP host/port).' } }
    }
    if (e.status) throw e
    throw { status: 0, data: { detail: 'Network error — is the backend running?' } }
  } finally {
    if (timer) clearTimeout(timer)
  }
}
