import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
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

  it('hides the Notify Vendors button for non-admin/analyst roles', async () => {
    mockFetchRoutes([{ match: '/alerts', json: ALERTS }])
    render(<Alerts navigate={vi.fn()} user={{ role: 'VENDOR' }} />)
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    expect(screen.queryByText('✉ Notify Vendors')).not.toBeInTheDocument()
  })

  it('shows the Notify Vendors button for admins and sends on click', async () => {
    mockFetchRoutes([
      { match: '/alerts/notify', json: { sent: 2, skipped_no_email: 1, failed: 0 } },
      { match: '/alerts', json: ALERTS },
    ])
    const toast = vi.fn()
    render(<Alerts navigate={vi.fn()} user={{ role: 'ADMIN' }} toast={toast} />)
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    fireEvent.click(screen.getByText('✉ Notify Vendors'))
    await waitFor(() => expect(toast).toHaveBeenCalledWith(
      expect.stringContaining('2 vendors emailed'), 'success'
    ))
  })

  it('shows the disabled reason when alert emails are not configured', async () => {
    mockFetchRoutes([
      { match: '/alerts/notify', json: { sent: 0, disabled_reason: 'Alert emails are disabled — set ALERTS_EMAIL_ENABLED=true and configure SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env.' } },
      { match: '/alerts', json: ALERTS },
    ])
    const toast = vi.fn()
    render(<Alerts navigate={vi.fn()} user={{ role: 'ADMIN' }} toast={toast} />)
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    fireEvent.click(screen.getByText('✉ Notify Vendors'))
    await waitFor(() => expect(toast).toHaveBeenCalledWith(
      expect.stringContaining('ALERTS_EMAIL_ENABLED'), 'error'
    ))
  })

  it('renders sent notification history so the user can confirm whether an email actually went out', async () => {
    mockFetchRoutes([
      { match: '/alerts/notifications', json: [
        { id: 'n1', vendor_name: 'Acme Corp', recipient_email: 'acme@example.com', alert_type: 'EXPIRING_SOON', coverage_type: 'General Liability', urgency_bucket: '7', sent_at: '2026-07-20T10:00:00Z', success: true },
        { id: 'n2', vendor_name: 'Beta LLC', recipient_email: 'beta@example.com', alert_type: 'COMPLIANCE_ISSUE', coverage_type: null, urgency_bucket: 'NON_COMPLIANT', sent_at: '2026-07-19T09:00:00Z', success: false, error_message: 'SMTP timeout' },
      ] },
      { match: '/alerts', json: ALERTS },
    ])
    render(<Alerts navigate={vi.fn()} user={{ role: 'ADMIN' }} />)
    await waitFor(() => expect(screen.getByText('acme@example.com')).toBeInTheDocument())
    expect(screen.getByText('beta@example.com')).toBeInTheDocument()
    expect(screen.getByText('✓ Sent')).toBeInTheDocument()
    expect(screen.getByText('✕ Failed')).toBeInTheDocument()
  })

  it('shows an empty-state message in the history panel when nothing has been sent yet', async () => {
    mockFetchRoutes([
      { match: '/alerts/notifications', json: [] },
      { match: '/alerts', json: ALERTS },
    ])
    render(<Alerts navigate={vi.fn()} user={{ role: 'ADMIN' }} />)
    await waitFor(() => expect(screen.getByText(/No notification emails sent yet/)).toBeInTheDocument())
  })
})
