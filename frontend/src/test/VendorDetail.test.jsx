import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import VendorDetail from '../components/VendorDetail.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const VENDOR = {
  id: 'v1', name: 'Acme Corp', contact_name: 'Jane', email: 'jane@acme.com',
  phone: '555-1234', city: 'Austin', state: 'TX', status: 'COMPLIANT', risk_tier: 'LOW',
  gl_expiry: '2027-01-01', wc_expiry: '2027-01-01', diversity_types: ['WBE'],
}
const DOCS = [{ id: 'd1', filename: 'coi.pdf', document_type: 'COI', status: 'PROCESSED', file_size_bytes: 1024, created_at: '2026-01-01T00:00:00Z' }]
const SCORE = { vendor_id: 'v1', total_score: 82, grade: 'B', breakdown: { status_score: 40, document_score: 30, expiry_score: 12, diversity_score: 0 } }

describe('VendorDetail', () => {
  it('loads using the `id` prop (regression: previously received `vendorId` from App.jsx while destructuring `id`, so it never loaded)', async () => {
    mockFetchRoutes([
      { match: '/vendors/v1/documents', json: DOCS },
      { match: '/dashboard/vendors/v1/score', json: SCORE },
      { match: '/vendors/v1', json: VENDOR },
    ])
    render(<VendorDetail id="v1" navigate={vi.fn()} toast={vi.fn()} />)
    await waitFor(() => expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0))
    expect(screen.getByText('82/100')).toBeInTheDocument()
  })

  it('clicking a document row navigates to the "analysis" page key (regression: previously used the non-existent "analysis-detail" key)', async () => {
    mockFetchRoutes([
      { match: '/vendors/v1/documents/d1/analyses', json: [{ id: 'a1' }] },
      { match: '/vendors/v1/documents', json: DOCS },
      { match: '/dashboard/vendors/v1/score', json: SCORE },
      { match: '/vendors/v1', json: VENDOR },
    ])
    const navigate = vi.fn()
    render(<VendorDetail id="v1" navigate={navigate} toast={vi.fn()} />)
    await waitFor(() => screen.getByText('coi.pdf'))
    fireEvent.click(screen.getByText('coi.pdf'))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('analysis', 'a1'))
  })

  it('Edit button opens EditVendorModal pre-filled with the loaded vendor (regression: previously passed no `vendor` prop, crashing the modal on open)', async () => {
    mockFetchRoutes([
      { match: '/vendors/v1/documents', json: DOCS },
      { match: '/dashboard/vendors/v1/score', json: SCORE },
      { match: '/vendors/v1', json: VENDOR },
    ])
    render(<VendorDetail id="v1" navigate={vi.fn()} toast={vi.fn()} />)
    await waitFor(() => expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0))
    expect(() => fireEvent.click(screen.getByText('Edit'))).not.toThrow()
    // the modal's input should be pre-filled from the vendor prop, not blank
    expect(screen.getByDisplayValue('Acme Corp')).toBeInTheDocument()
  })
})
