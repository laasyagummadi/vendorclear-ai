import { useState } from 'react'
import { setToken } from '../api.js'

const API_BASE = 'http://localhost:8000/api/v1'

export default function Auth({ onLogin }) {
  const [tab, setTab] = useState('login')
  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [regForm, setRegForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [loginErr, setLoginErr] = useState('')
  const [regErr, setRegErr] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [regLoading, setRegLoading] = useState(false)

  async function doLogin(email, pwd) {
    setLoginLoading(true); setLoginErr('')
    try {
      const res = await fetch(API_BASE + '/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: pwd })
      })
      const data = await res.json()
      if (!res.ok) {
        let msg = data.error || data.detail || 'Login failed';
        if (data.details && Array.isArray(data.details)) {
          msg = data.details.map(d => `${d.field}: ${d.message}`).join(', ');
        }
        setLoginErr(msg);
        return;
      }
      setToken(data.access_token)
      onLogin()
    } catch (e) {
      setLoginErr('Cannot reach backend. Is it running on port 8000?')
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
      const res = await fetch(API_BASE + '/auth/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: name, email, password, confirm_password: confirm })
      })
      const data = await res.json()
      if (!res.ok) {
        let msg = data.error || data.detail || 'Registration failed';
        if (data.details && Array.isArray(data.details)) {
          msg = data.details.map(d => `${d.field}: ${d.message}`).join(', ');
        }
        setRegErr(msg);
        return;
      }
      setTab('login')
      setLoginForm({ email, password })
      await doLogin(email, password)
    } catch (e) {
      setRegErr('Cannot reach backend')
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
