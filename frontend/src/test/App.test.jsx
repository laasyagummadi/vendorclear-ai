import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App.jsx'
import { setToken } from '../api.js'
import { mockFetchRoutes } from '../test/mockFetch.js'

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
    setToken('')
  })

  it('shows the Auth screen when there is no token', () => {
    mockFetchRoutes([])
    render(<App />)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('an expired/invalid token triggers a clean logout with an explanatory toast (regression: setUnauthHandler was exported but never called, so 401s silently left every page blank forever)', async () => {
    setToken('stale-token')
    mockFetchRoutes([
      { match: '/auth/me', status: 401, json: { success: false, error: 'Invalid or expired token' } },
      { match: '/alerts', status: 401, json: { success: false, error: 'Invalid or expired token' } },
    ])
    render(<App />)

    await waitFor(() => expect(screen.getByText('Your session expired. Please sign in again.')).toBeInTheDocument())
    // exactly one toast, even though both /auth/me and /alerts 401 concurrently
    expect(screen.getAllByText('Your session expired. Please sign in again.').length).toBe(1)
    // and it actually returns to the login screen, not just shows a toast
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders the authenticated shell (sidebar + dashboard) with a valid token', async () => {
    setToken('valid-token')
    mockFetchRoutes([
      { match: '/auth/me', json: { id: 'u1', email: 'demo@vc.ai', full_name: 'Demo User' } },
      { match: '/alerts', json: { total: 2, expiry_alerts: [], compliance_alerts: [] } },
      { match: '/dashboard/summary', json: { vendors: {}, risk_tiers: {}, documents: {}, analyses: {}, alerts: {} } },
    ])
    render(<App />)
    await waitFor(() => expect(screen.getByText('Demo User')).toBeInTheDocument())
    expect(screen.getByText('VendorClear AI')).toBeInTheDocument()
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
  })
})
