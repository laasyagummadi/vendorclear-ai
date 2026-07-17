import { useState } from 'react'
import { api, setToken } from '../api.js'

export default function Auth({ onLogin }) {
  const [tab, setTab] = useState('login')
  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [regForm, setRegForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [loginErr, setLoginErr] = useState('')
  const [regErr, setRegErr] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [regLoading, setRegLoading] = useState(false)

  // NOTE: previously this called onLogin() with no arguments, but App.jsx's
  // login(tok, userObj) needs both to update its React state. That meant a
  // successful login/register never actually navigated into the app — the
  // token was stored in localStorage (so a manual refresh "fixed" it) but
  // the UI stayed stuck on the auth screen. Fixed by fetching /auth/me and
  // passing both values through.
  async function doLogin(email, pwd) {
    setLoginLoading(true); setLoginErr('')
    try {
      const data = await api('POST', '/auth/login', { email, password: pwd })
      if (!data) { setLoginErr('Login failed'); return }
      setToken(data.access_token)
      const user = await api('GET', '/auth/me')
      onLogin(data.access_token, user)
    } catch (e) {
      setLoginErr(e?.data?.error || e?.data?.detail || 'Cannot reach backend. Is it running on port 8000?')
    } finally { setLoginLoading(false) }
  }

  async function handleLogin(e) {
    e.preventDefault()
    const { email, password } = loginForm
    if (!email || !password) { setLoginErr('Please enter email and password'); return }
    await doLogin(email, password)
  }

  async function handleRegister(e) {
    e.preventDefault()
    const { name, email, password, confirm } = regForm
    if (!name || !email || !password) { setRegErr('All fields are required'); return }
    if (password !== confirm) { setRegErr('Passwords do not match'); return }
    setRegLoading(true); setRegErr('')
    try {
      await api('POST', '/auth/register', {
        full_name: name, email, password, confirm_password: confirm,
      })
      setTab('login')
      setLoginForm({ email, password })
      await doLogin(email, password)
    } catch (e) {
      setRegErr(e?.data?.error || e?.data?.detail || (e?.data?.details && e.data.details[0]?.message) || 'Cannot reach backend')
    } finally { setRegLoading(false) }
  }

  return (
    <div className="auth-screen">
      <div className="auth-box">
        <div className="auth-logo">
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ width: 36, height: 36, background: '#fff', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#000" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span className="auth-title">VendorClear AI</span>
          </div>
          <div className="auth-sub">Vendor Intelligence, Clarity Assured</div>
        </div>

        <div className="auth-tab">
          <div className={`auth-tab-btn ${tab === 'login' ? 'active' : ''}`} onClick={() => { setTab('login'); setLoginErr(''); setRegErr('') }}>Sign In</div>
          <div className={`auth-tab-btn ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setLoginErr(''); setRegErr('') }}>Register</div>
        </div>

        {tab === 'login' && (
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input type="email" className="form-input" placeholder="you@company.com"
                value={loginForm.email} onChange={e => setLoginForm(f => ({ ...f, email: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input type="password" className="form-input" placeholder="••••••••"
                value={loginForm.password} onChange={e => setLoginForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <button type="submit" className="btn btn-primary w-full" style={{ justifyContent: 'center', padding: 11 }} disabled={loginLoading}>
              {loginLoading ? <span className="spinner" /> : 'Sign In'}
            </button>
            {loginErr && <div style={{ color: '#f87171', fontSize: 12, textAlign: 'center', marginTop: 12 }}>{loginErr}</div>}
          </form>
        )}

        {tab === 'register' && (
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label">Full name</label>
              <input type="text" className="form-input" placeholder="Jane Smith"
                value={regForm.name} onChange={e => setRegForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input type="email" className="form-input" placeholder="you@company.com"
                value={regForm.email} onChange={e => setRegForm(f => ({ ...f, email: e.target.value }))} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Password</label>
                <input type="password" className="form-input" placeholder="••••••••"
                  value={regForm.password} onChange={e => setRegForm(f => ({ ...f, password: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Confirm</label>
                <input type="password" className="form-input" placeholder="••••••••"
                  value={regForm.confirm} onChange={e => setRegForm(f => ({ ...f, confirm: e.target.value }))} />
              </div>
            </div>
            <button type="submit" className="btn btn-primary w-full" style={{ justifyContent: 'center', padding: 11 }} disabled={regLoading}>
              {regLoading ? <span className="spinner" /> : 'Create Account'}
            </button>
            {regErr && <div style={{ color: '#f87171', fontSize: 12, textAlign: 'center', marginTop: 12 }}>{regErr}</div>}
          </form>
        )}

        <div style={{ marginTop: 20, textAlign: 'center', fontSize: 11, color: '#2a2a2a' }}>
          Backend must be running on <span style={{ color: '#444' }}>http://localhost:8000</span>
        </div>
      </div>
    </div>
  )
}
