import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '../components/Dashboard.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const SUMMARY = {
  generated_at: '2026-07-13T00:00:00Z',
  vendors: { total: 10, active: 10, compliant: 5, needs_review: 3, non_compliant: 2, compliance_rate_pct: 50.0 },
  risk_tiers: { low: 5, medium: 3, high: 2 },
  documents: { total: 4, processed: 3, pending: 1, failed: 0, coi_count: 2, diversity_cert_count: 2 },
  analyses: { compliant: 2, needs_review: 1, non_compliant: 1 },
  alerts: { total: 8, expiry: 3, compliance: 5, expiring_within_30_days: 3, expiring_within_7_days: 1 },
}

describe('Dashboard', () => {
  it('renders real vendor/document/alert counts from the fixed backend contract', async () => {
    mockFetchRoutes([{ match: '/dashboard/summary', json: SUMMARY }])
    render(<Dashboard navigate={vi.fn()} toast={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('10')).toBeInTheDocument()) // total vendors
    expect(screen.getByText('10 active')).toBeInTheDocument()               // regression: vendors.active
    expect(screen.getByText('50%')).toBeInTheDocument()                     // compliance rate
    expect(screen.getByText('8')).toBeInTheDocument()                      // open alerts total
    expect(screen.getByText('3 expiry · 5 compliance')).toBeInTheDocument() // regression: alerts.expiry/compliance
    expect(screen.getByText('View Alerts (8)')).toBeInTheDocument()
  })

  it('does not crash and shows dashes when the summary fetch fails', async () => {
    mockFetchRoutes([{ match: '/dashboard/summary', status: 500, json: { success: false, error: 'boom' } }])
    expect(() => render(<Dashboard navigate={vi.fn()} toast={vi.fn()} />)).not.toThrow()
    await waitFor(() => expect(screen.getAllByText('—').length).toBeGreaterThan(0))
  })
})
