import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import CreateVendorModal from '../components/modals/CreateVendorModal.jsx'
import EditVendorModal from '../components/modals/EditVendorModal.jsx'
import UploadModal from '../components/modals/UploadModal.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

describe('CreateVendorModal', () => {
  it('posts to the exact registered route with no trailing slash (regression: previously posted to /vendors/, causing a 307 redirect)', async () => {
    const fetchMock = mockFetchRoutes([
      { match: '/vendors', json: { id: 'v9', name: 'New Co' } },
    ])
    const onCreated = vi.fn()
    render(<CreateVendorModal onClose={vi.fn()} onCreated={onCreated} />)
    fireEvent.change(screen.getByPlaceholderText('Acme Corp'), { target: { value: 'New Co' } })
    fireEvent.click(screen.getByRole('button', { name: /create vendor/i }))

    await waitFor(() => expect(onCreated).toHaveBeenCalled())
    const url = fetchMock.mock.calls[0][0]
    expect(url.endsWith('/vendors')).toBe(true)
    expect(url.endsWith('/vendors/')).toBe(false)
  })

  it('shows the real backend error message on failure (regression: previously read ex.message on a plain object, always undefined)', async () => {
    mockFetchRoutes([{ match: '/vendors', status: 422, json: { success: false, error: 'Vendor name is required' } }])
    render(<CreateVendorModal onClose={vi.fn()} onCreated={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Acme Corp'), { target: { value: 'X' } })
    fireEvent.click(screen.getByRole('button', { name: /create vendor/i }))
    await waitFor(() => expect(screen.getByText('Vendor name is required')).toBeInTheDocument())
  })
})

describe('EditVendorModal', () => {
  const VENDOR = {
    id: 'v1', name: 'Acme Corp', contact_name: 'Jane', email: 'jane@acme.com', phone: '555-1234',
    address: '', city: 'Austin', state: 'TX', zip_code: '78701', status: 'COMPLIANT', risk_tier: 'LOW',
    gl_expiry: '2027-01-01', wc_expiry: '2027-01-01', notes: '',
  }

  it('renders pre-filled without crashing given a real vendor object (regression: previously crashed with vendor=undefined)', () => {
    expect(() =>
      render(<EditVendorModal vendor={VENDOR} onClose={vi.fn()} onUpdated={vi.fn()} />)
    ).not.toThrow()
    expect(screen.getByDisplayValue('Acme Corp')).toBeInTheDocument()
    expect(screen.getByDisplayValue('jane@acme.com')).toBeInTheDocument()
  })

  it('renders nothing (not a crash) when vendor is not yet available', () => {
    const { container } = render(<EditVendorModal vendor={null} onClose={vi.fn()} onUpdated={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('submits via PATCH to /vendors/{id} with valid enum values (regression: previously used PUT and invalid enum options)', async () => {
    const fetchMock = mockFetchRoutes([{ match: '/vendors/v1', json: { ...VENDOR, name: 'Acme Corp Updated' } }])
    const onUpdated = vi.fn()
    render(<EditVendorModal vendor={VENDOR} onClose={vi.fn()} onUpdated={onUpdated} />)
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(onUpdated).toHaveBeenCalled())
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toContain('/vendors/v1')
    expect(opts.method).toBe('PATCH')
    const body = JSON.parse(opts.body)
    expect(['COMPLIANT', 'NEEDS_REVIEW', 'NON_COMPLIANT']).toContain(body.status)
    expect(['LOW', 'MEDIUM', 'HIGH']).toContain(body.risk_tier)
  })
})

describe('UploadModal', () => {
  it('posts to the exact registered upload route (regression: previously posted to a URL with an extra "/upload" segment that always 404d)', async () => {
    const fetchMock = mockFetchRoutes([
      { match: '/vendors/v1/documents', json: { document: { id: 'd1' }, message: 'ok' } },
    ])
    const onUploaded = vi.fn()
    render(<UploadModal vendorId="v1" vendorName="Acme Corp" onClose={vi.fn()} onUploaded={onUploaded} />)

    const file = new File(['%PDF-1.4 fake'], 'coi.pdf', { type: 'application/pdf' })
    const input = document.querySelector('input[type="file"]')
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: /upload & analyze/i }))

    await waitFor(() => expect(onUploaded).toHaveBeenCalled())
    const url = fetchMock.mock.calls[0][0]
    expect(url).toMatch(/\/vendors\/v1\/documents$/)
  })

  it('sends doc_type_hint as a form field (regression: previously sent doc_type, which the backend ignores)', async () => {
    const fetchMock = mockFetchRoutes([
      { match: '/vendors/v1/documents', json: { document: { id: 'd1' }, message: 'ok' } },
    ])
    render(<UploadModal vendorId="v1" vendorName="Acme Corp" onClose={vi.fn()} onUploaded={vi.fn()} />)
    const file = new File(['%PDF-1.4 fake'], 'coi.pdf', { type: 'application/pdf' })
    const input = document.querySelector('input[type="file"]')
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: /upload & analyze/i }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const formData = fetchMock.mock.calls[0][1].body
    expect(formData.has('doc_type_hint')).toBe(true)
    expect(formData.has('doc_type')).toBe(false)
  })
})
