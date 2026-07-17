import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Auth from '../components/Auth.jsx'
import { setToken } from '../api.js'
import { mockFetchRoutes } from '../test/mockFetch.js'

describe('Auth', () => {
  beforeEach(() => {
    localStorage.clear()
    setToken('') // reset api.js's module-level token between tests
  })

  it('login success calls onLogin with BOTH token and user (regression: previously called with no args)', async () => {
    mockFetchRoutes([
      { match: '/auth/login', json: { access_token: 'tok123', refresh_token: 'r1', token_type: 'bearer' } },
      { match: '/auth/me', json: { id: 'u1', email: 'demo@vc.ai', full_name: 'Demo User' } },
    ])
    const onLogin = vi.fn()
    render(<Auth onLogin={onLogin} />)

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), { target: { value: 'demo@vc.ai' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'Secure123' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(onLogin).toHaveBeenCalledTimes(1))
    expect(onLogin).toHaveBeenCalledWith('tok123', { id: 'u1', email: 'demo@vc.ai', full_name: 'Demo User' })
  })

  it('shows a real error message on failed login instead of a generic one', async () => {
    mockFetchRoutes([
      { match: '/auth/login', status: 401, json: { success: false, error: 'Invalid email or password' } },
    ])
    render(<Auth onLogin={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('you@company.com'), { target: { value: 'demo@vc.ai' } })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(screen.getByText('Invalid email or password')).toBeInTheDocument())
  })

  it('register success flow chains into a real login (regression: previously stuck on the auth screen)', async () => {
    mockFetchRoutes([
      { match: '/auth/register', json: { user: { id: 'u2' }, message: 'ok' } },
      { match: '/auth/login', json: { access_token: 'tok456', refresh_token: 'r2', token_type: 'bearer' } },
      { match: '/auth/me', json: { id: 'u2', email: 'new@vc.ai', full_name: 'New User' } },
    ])
    const onLogin = vi.fn()
    render(<Auth onLogin={onLogin} />)

    fireEvent.click(screen.getByText('Register'))
    fireEvent.change(screen.getByPlaceholderText('Jane Smith'), { target: { value: 'New User' } })
    fireEvent.change(screen.getByPlaceholderText('you@company.com'), { target: { value: 'new@vc.ai' } })
    const pwFields = screen.getAllByPlaceholderText('••••••••')
    fireEvent.change(pwFields[0], { target: { value: 'Secure123' } })
    fireEvent.change(pwFields[1], { target: { value: 'Secure123' } })
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(onLogin).toHaveBeenCalledWith('tok456', { id: 'u2', email: 'new@vc.ai', full_name: 'New User' }))
  })
})
