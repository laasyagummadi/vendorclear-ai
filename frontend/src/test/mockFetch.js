import { vi } from 'vitest'

/**
 * Installs a global.fetch mock driven by an ordered list of
 * { match: string|RegExp, status, json } rules. The first matching rule
 * for a given URL is used every time that URL is requested, unless
 * `once: true` is set, in which case it's consumed after one match.
 */
export function mockFetchRoutes(rules) {
  const used = new Set()
  global.fetch = vi.fn((url, opts = {}) => {
    const idx = rules.findIndex((r, i) => {
      if (r.once && used.has(i)) return false
      return typeof r.match === 'string' ? url.includes(r.match) : r.match.test(url)
    })
    if (idx === -1) {
      return Promise.resolve({
        status: 404,
        ok: false,
        headers: { get: () => 'application/json' },
        json: async () => ({ success: false, error: 'no mock route for ' + url }),
      })
    }
    const rule = rules[idx]
    if (rule.once) used.add(idx)
    const status = rule.status ?? 200
    return Promise.resolve({
      status,
      ok: status >= 200 && status < 300,
      headers: { get: () => 'application/json' },
      json: async () => rule.json,
    })
  })
  return global.fetch
}

export function clearFetchMock() {
  if (global.fetch && global.fetch.mockClear) global.fetch.mockClear()
}
