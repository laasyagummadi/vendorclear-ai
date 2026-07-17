import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import Vendors from '../components/Vendors.jsx'
import { mockFetchRoutes } from '../test/mockFetch.js'

const PAGINATED_RESPONSE = {
  success: true,
  data: [
    { id: 'v1', name: 'Acme Corp', email: 'a@acme.com', city: 'Austin', state: 'TX', risk_tier: 'LOW', status: 'COMPLIANT', gl_expiry: '2027-01-01' },
    { id: 'v2', name: 'Beta LLC', email: 'b@beta.com', city: 'Dallas', state: 'TX', risk_tier: 'HIGH', status: 'NON_COMPLIANT', gl_expiry: '2024-01-01' },
  ],
  total: 2, page: 1, page_size: 100, total_pages: 1,
}

describe('Vendors', () => {
  it('renders the vendor list from the real paginated envelope without crashing (regression: previously called .filter/.map on the whole {data:[...]} object)', async () => {
    mockFetchRoutes([{ match: '/vendors?page=1&page_size=100', json: PAGINATED_RESPONSE }])
    render(<Vendors navigate={vi.fn()} toast={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument())
    expect(screen.getByText('Beta LLC')).toBeInTheDocument()
    expect(screen.getByText('2 total vendors')).toBeInTheDocument()
  })

  it('requests the correct page/page_size query params (regression: previously sent skip/limit, which the backend ignores)', async () => {
    const fetchMock = mockFetchRoutes([{ match: 'page=1&page_size=100', json: PAGINATED_RESPONSE }])
    render(<Vendors navigate={vi.fn()} toast={vi.fn()} />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const calledUrl = fetchMock.mock.calls[0][0]
    expect(calledUrl).toContain('page=1')
    expect(calledUrl).toContain('page_size=100')
    expect(calledUrl).not.toContain('skip=')
  })

  it('shows an empty state instead of crashing when there are no vendors', async () => {
    mockFetchRoutes([{ match: '/vendors', json: { success: true, data: [], total: 0, page: 1, page_size: 100, total_pages: 0 } }])
    render(<Vendors navigate={vi.fn()} toast={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('No vendors yet.')).toBeInTheDocument())
  })

  it('clicking a vendor row navigates to vendor-detail with its id', async () => {
    mockFetchRoutes([{ match: '/vendors?page=1&page_size=100', json: PAGINATED_RESPONSE }])
    const navigate = vi.fn()
    render(<Vendors navigate={navigate} toast={vi.fn()} />)
    await waitFor(() => screen.getByText('Acme Corp'))
    fireEvent.click(screen.getByText('Acme Corp'))
    expect(navigate).toHaveBeenCalledWith('vendor-detail', 'v1')
  })

  it('search filter narrows the list client-side', async () => {
    mockFetchRoutes([{ match: '/vendors?page=1&page_size=100', json: PAGINATED_RESPONSE }])
    render(<Vendors navigate={vi.fn()} toast={vi.fn()} />)
    await waitFor(() => screen.getByText('Acme Corp'))
    fireEvent.change(screen.getByPlaceholderText('Search vendors…'), { target: { value: 'beta' } })
    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument()
    expect(screen.getByText('Beta LLC')).toBeInTheDocument()
  })
})
