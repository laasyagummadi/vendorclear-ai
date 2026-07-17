import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Alerts from '../components/Alerts.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const ALERTS = {
  total: 2,
  expiry_alerts: [
    { vendor_id: 'v1', vendor_name: 'Acme Corp', alert_type: 'EXPIRING_SOON', coverage_type: 'General Liability', expiry_date: '2026-08-01', days_until_expiry: 19, severity: 'HIGH' },
  ],
  compliance_alerts: [
    { vendor_id: 'v2', vendor_name: 'Beta LLC', alert_type: 'NON_COMPLIANT', status: 'NON_COMPLIANT', risk_tier: 'HIGH', severity: 'CRITICAL' },
  ],
}

describe('Alerts', () => {
  it('shows the coverage type label (regression: previously read a.document_type, which the backend never sends, leaving this blank)', async () => {
    mockFetchRoutes([{ match: '/alerts', json: ALERTS }])
    render(<Alerts navigate={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    expect(screen.getByText(/General Liability expires in/)).toBeInTheDocument()
  })

  it('renders compliance alerts with status badges', async () => {
    mockFetchRoutes([{ match: '/alerts', json: ALERTS }])
    render(<Alerts navigate={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Beta LLC')).toBeInTheDocument())
    expect(screen.getByText('NON_COMPLIANT')).toBeInTheDocument()
  })

  it('shows empty states when there are no alerts', async () => {
    mockFetchRoutes([{ match: '/alerts', json: { total: 0, expiry_alerts: [], compliance_alerts: [] } }])
    render(<Alerts navigate={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('No expiry alerts')).toBeInTheDocument())
    expect(screen.getByText('No compliance alerts')).toBeInTheDocument()
  })
})
