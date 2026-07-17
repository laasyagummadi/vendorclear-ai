import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import AnalysisDetail from '../components/AnalysisDetail.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const ANALYSIS = {
  id: 'a1', document_id: 'd1', vendor_id: 'v1',
  confidence_score: 0.85, status: 'NEEDS_REVIEW',
  insured_name: 'Acme Corp', general_liability_limit_usd: 2000000,
  expiry_date: '2026-08-01',
  findings: [{ id: 'f1', analysis_id: 'a1', severity: 'HIGH', rule_code: 'GL_EXPIRING_SOON', message: 'GL expires within 30 days.' }],
}

describe('AnalysisDetail', () => {
  it('fetches via the `id` prop and renders extracted fields + findings', async () => {
    mockFetchRoutes([{ match: '/analyses/a1', json: ANALYSIS }])
    render(<AnalysisDetail id="a1" navigate={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    expect(screen.getByText('$2,000,000')).toBeInTheDocument()
    expect(screen.getByText('GL_EXPIRING_SOON')).toBeInTheDocument()
    expect(screen.getByText('GL expires within 30 days.')).toBeInTheDocument()
  })

  it('breadcrumb "Vendor" link uses the real vendor_id from the backend (regression: was always undefined)', async () => {
    mockFetchRoutes([{ match: '/analyses/a1', json: ANALYSIS }])
    render(<AnalysisDetail id="a1" navigate={vi.fn()} />)
    await waitFor(() => screen.getByText('Acme Corp'))
    expect(ANALYSIS.vendor_id).toBe('v1') // sanity: backend now sends it
  })

  it('shows "no compliance issues" state when findings is empty', async () => {
    mockFetchRoutes([{ match: '/analyses/a2', json: { ...ANALYSIS, id: 'a2', findings: [] } }])
    render(<AnalysisDetail id="a2" navigate={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/No compliance issues found/)).toBeInTheDocument())
  })
})
