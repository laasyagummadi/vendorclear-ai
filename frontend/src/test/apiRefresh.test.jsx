import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, setToken, setRefreshToken, setUnauthHandler } from '../api.js'

describe('api.js token refresh', () => {
  beforeEach(() => {
    localStorage.clear()
    setToken('')
    setRefreshToken('')
    setUnauthHandler(null)
    vi.restoreAllMocks()
  })

  it('silently refreshes the access token on a 401 and replays the original request', async () => {
    setToken('expired-token')
    setRefreshToken('good-refresh')

    let call = 0
    global.fetch = vi.fn((url) => {
      call++
      // 1st: original request -> 401 (expired token)
      if (call === 1) {
        return Promise.resolve({ status: 401, ok: false, headers: { get: () => 'application/json' }, json: async () => ({ error: 'expired' }) })
      }
      // 2nd: refresh call -> new tokens
      if (url.includes('/auth/refresh')) {
        return Promise.resolve({ status: 200, ok: true, headers: { get: () => 'application/json' }, json: async () => ({ access_token: 'fresh-token', refresh_token: 'new-refresh' }) })
      }
      // 3rd: replayed original request -> success
      return Promise.resolve({ status: 200, ok: true, headers: { get: () => 'application/json' }, json: async () => ({ ok: true, replayed: true }) })
    })

    const onUnauth = vi.fn()
    setUnauthHandler(onUnauth)

    const result = await api('GET', '/vendors')
    expect(result).toEqual({ ok: true, replayed: true })
    expect(onUnauth).not.toHaveBeenCalled()          // no logout — refresh succeeded
    expect(localStorage.getItem('vc_token')).toBe('fresh-token')  // token was rotated
  })

  it('logs out when the refresh token is also invalid', async () => {
    setToken('expired-token')
    setRefreshToken('bad-refresh')

    global.fetch = vi.fn((url) => {
      if (url.includes('/auth/refresh')) {
        return Promise.resolve({ status: 401, ok: false, headers: { get: () => 'application/json' }, json: async () => ({ error: 'invalid refresh' }) })
      }
      return Promise.resolve({ status: 401, ok: false, headers: { get: () => 'application/json' }, json: async () => ({ error: 'expired' }) })
    })

    const onUnauth = vi.fn()
    setUnauthHandler(onUnauth)

    const result = await api('GET', '/vendors')
    expect(result).toBeNull()
    expect(onUnauth).toHaveBeenCalledTimes(1)         // clean logout fired
    expect(localStorage.getItem('vc_refresh')).toBeNull()  // refresh token cleared
  })

  it('does not attempt refresh for unauthenticated requests (e.g. a failed login)', async () => {
    setToken('')          // no token — this is a public call
    setRefreshToken('')

    global.fetch = vi.fn(() =>
      Promise.resolve({ status: 401, ok: false, headers: { get: () => 'application/json' }, json: async () => ({ error: 'Invalid email or password' }) })
    )
    const onUnauth = vi.fn()
    setUnauthHandler(onUnauth)

    // a 401 with no token should surface as a thrown error, not a logout
    await expect(api('POST', '/auth/login', { email: 'x', password: 'y' })).rejects.toMatchObject({ status: 401 })
    expect(onUnauth).not.toHaveBeenCalled()
    expect(global.fetch).toHaveBeenCalledTimes(1)     // no refresh attempt
  })

  it('surfaces a 403 (role/permission denied) as a thrown error WITHOUT logging the user out (regression: previously treated identically to an expired session)', async () => {
    setToken('valid-token')
    setRefreshToken('valid-refresh')

    global.fetch = vi.fn(() =>
      Promise.resolve({
        status: 403,
        ok: false,
        headers: { get: () => 'application/json' },
        json: async () => ({ success: false, error: 'Your role (VENDOR) does not have permission to perform this action. Requires: ADMIN, ANALYST.' }),
      })
    )
    const onUnauth = vi.fn()
    setUnauthHandler(onUnauth)

    await expect(api('POST', '/alerts/notify')).rejects.toMatchObject({
      status: 403,
      data: { error: expect.stringContaining('does not have permission') },
    })
    expect(onUnauth).not.toHaveBeenCalled()               // must NOT force a logout
    expect(localStorage.getItem('vc_token')).toBe('valid-token')  // session left intact
  })
})
