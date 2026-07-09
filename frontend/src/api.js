const API_BASE = (window.API_BASE || 'http://localhost:8000') + '/api/v1'

let _token = localStorage.getItem('vc_token') || ''
let _onUnauth = null

export function setToken(t) { _token = t; if (t) localStorage.setItem('vc_token', t); else localStorage.removeItem('vc_token') }
export function getToken() { return _token }
export function setUnauthHandler(fn) { _onUnauth = fn }

export async function api(method, path, body = null, isForm = false) {
  const headers = {}
  if (_token) headers['Authorization'] = 'Bearer ' + _token
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const opts = { method, headers }
  if (body) opts.body = isForm ? body : JSON.stringify(body)
  try {
    const res = await fetch(API_BASE + path, opts)
    if (res.status === 401 || res.status === 403) { if (_onUnauth) _onUnauth(); return null }
    const ct = res.headers.get('content-type') || ''
    const data = ct.includes('application/json') ? await res.json() : await res.text()
    if (!res.ok) throw { status: res.status, data }
    return data
  } catch (e) {
    if (e.status) throw e
    throw { status: 0, data: { detail: 'Network error — is the backend running?' } }
  }
}
