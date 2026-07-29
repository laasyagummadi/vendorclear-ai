import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import Report from '../components/Report.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const REPORT = {
  report_date: '2026-07-13',
  summary: { total_vendors: 2, compliant: 1, non_compliant: 1, avg_score: 65.5 },
  vendors: [
    { id: 'v1', name: 'Acme Corp', email: 'a@acme.com', status: 'COMPLIANT', risk_tier: 'LOW', total_score: 91, grade: 'A', document_count: 3, gl_expiry: '2027-01-01' },
    { id: 'v2', name: 'Beta LLC', email: 'b@beta.com', status: 'NON_COMPLIANT', risk_tier: 'HIGH', total_score: 40, grade: 'F', document_count: 0, gl_expiry: '2024-01-01' },
  ],
}

describe('Report', () => {
  it('renders summary and per-vendor fields using the real backend field names (regression: previously read total_vendors/avg_score/id/name/total_score/document_count that the backend never sent)', async () => {
    mockFetchRoutes([{ match: '/dashboard/compliance-report', json: REPORT }])
    render(<Report navigate={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    expect(screen.getAllByText('2').length).toBeGreaterThan(0) // total_vendors stat
    expect(screen.getByText('66')).toBeInTheDocument()  // avg_score rounded
    expect(screen.getByText('91')).toBeInTheDocument()  // vendor total_score
    expect(screen.getByText('3 docs')).toBeInTheDocument() // document_count
    expect(screen.getByText('A')).toBeInTheDocument()   // grade
  })

  it('clicking a vendor row navigates using the real vendor id', async () => {
    mockFetchRoutes([{ match: '/dashboard/compliance-report', json: REPORT }])
    const navigate = vi.fn()
    render(<Report navigate={navigate} />)
    await waitFor(() => screen.getByText('Acme Corp'))
    fireEvent.click(screen.getByText('Acme Corp'))
    expect(navigate).toHaveBeenCalledWith('vendor-detail', 'v1')
  })
})
