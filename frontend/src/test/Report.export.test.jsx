import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import Report from '../components/Report.jsx'
import { setToken, setRefreshToken } from '../api.js'

const REPORT = {
  report_date: '2026-07-22',
  summary: { total_vendors: 1, compliant: 1, non_compliant: 0, avg_score: 91 },
  vendors: [
    { id: 'v1', name: 'Acme Corp', email: 'a@acme.com', status: 'COMPLIANT', risk_tier: 'LOW', total_score: 91, grade: 'A', document_count: 3, gl_expiry: '2027-01-01' },
  ],
}

// Minimal fetch mock that can serve JSON for the report load and either a
// blob or an error status for the export endpoint, mirroring real Response
// behavior closely enough for the code under test (unlike mockFetchRoutes,
// which only ever returns JSON).
function mockFetchWithExport({ exportStatus = 200, exportOnce } = {}) {
  let exportCalls = 0
  global.fetch = vi.fn((url) => {
    if (url.includes('/dashboard/compliance-report/export')) {
      exportCalls++
      const status = typeof exportOnce === 'function' ? exportOnce(exportCalls) : exportStatus
      return Promise.resolve({
        status,
        ok: status >= 200 && status < 300,
        headers: { get: () => 'text/csv' },
        json: async () => ({ detail: 'Not authenticated' }),
        blob: async () => new Blob(['name,email\nAcme Corp,a@acme.com'], { type: 'text/csv' }),
      })
    }
    if (url.includes('/auth/refresh')) {
      return Promise.resolve({
        status: 200, ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ access_token: 'new-token' }),
      })
    }
    return Promise.resolve({
      status: 200, ok: true,
      headers: { get: () => 'application/json' },
      json: async () => REPORT,
    })
  })
  return () => exportCalls
}

describe('Report — CSV export', () => {
  beforeEach(() => {
    setToken('test-token')
    setRefreshToken('')
    global.URL.createObjectURL = vi.fn(() => 'blob:mock')
    global.URL.revokeObjectURL = vi.fn()
  })
  afterEach(() => {
    setToken('')
    vi.restoreAllMocks()
  })

  it('downloads the CSV on a normal successful export and confirms it via toast', async () => {
    mockFetchWithExport({ exportStatus: 200 })
    const toast = vi.fn()
    render(<Report navigate={vi.fn()} toast={toast} />)
    await waitFor(() => screen.getByText('Acme Corp'))

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    fireEvent.click(screen.getByText(/Export CSV/i))

    await waitFor(() => expect(clickSpy).toHaveBeenCalled())
    expect(screen.queryByTestId('export-error')).not.toBeInTheDocument()
    // Regression: a successful export previously gave zero visible feedback,
    // which was indistinguishable from the button doing nothing at all.
    expect(toast).toHaveBeenCalledWith(expect.stringMatching(/exported/i), 'success')
  })

  it('shows a visible error instead of failing silently when the export request errors', async () => {
    mockFetchWithExport({ exportStatus: 500 })
    const toast = vi.fn()
    render(<Report navigate={vi.fn()} toast={toast} />)
    await waitFor(() => screen.getByText('Acme Corp'))

    fireEvent.click(screen.getByText(/Export CSV/i))

    await waitFor(() => expect(screen.getByTestId('export-error')).toBeInTheDocument())
    expect(toast).toHaveBeenCalledWith(expect.any(String), 'error')
  })

  it('transparently refreshes an expired access token and retries the export once', async () => {
    setRefreshToken('a-refresh-token')
    const getExportCalls = mockFetchWithExport({
      // First export attempt looks like an expired token (401); after the
      // refresh call succeeds, the retried export attempt should succeed.
      exportOnce: (n) => (n === 1 ? 401 : 200),
    })
    render(<Report navigate={vi.fn()} />)
    await waitFor(() => screen.getByText('Acme Corp'))

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    fireEvent.click(screen.getByText(/Export CSV/i))

    await waitFor(() => expect(clickSpy).toHaveBeenCalled())
    expect(getExportCalls()).toBe(2)
    expect(screen.queryByTestId('export-error')).not.toBeInTheDocument()
  })
})
