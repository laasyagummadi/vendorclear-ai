import { useState, useEffect, useRef } from 'react'
import { getToken, setToken, setUnauthHandler, api } from './api.js'
import Auth from './components/Auth.jsx'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './components/Dashboard.jsx'
import Vendors from './components/Vendors.jsx'
import VendorDetail from './components/VendorDetail.jsx'
import AnalysisDetail from './components/AnalysisDetail.jsx'
import Alerts from './components/Alerts.jsx'
import Report from './components/Report.jsx'
import Toast from './components/Toast.jsx'

export default function App() {
  const [token, setTokenState] = useState(() => getToken())
  const [user, setUser] = useState(null)
  const [page, setPage] = useState('dashboard')
  const [pageParam, setPageParam] = useState(null)
  const [toasts, setToasts] = useState([])
  const [alertCount, setAlertCount] = useState(0)

  function toast(msg, type = 'success') {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
  }

  const loggedOutRef = useRef(false)

  function logout(message) {
    if (loggedOutRef.current) return // avoid duplicate toasts from concurrent 401s
    loggedOutRef.current = true
    setToken('')
    setTokenState('')
    setUser(null)
    setPage('dashboard')
    setPageParam(null)
    if (message) toast(message, 'error')
  }

  // NOTE: api.js exposes setUnauthHandler() for exactly this purpose but it
  // was never called anywhere in the app. That meant every api() call
  // silently returned null on a 401/403 (expired/invalid token) with no
  // handler firing — pages just went blank forever with zero indication
  // the user needed to log back in, and no way back to the login screen
  // short of a manual page refresh. Now any 401/403 forces a clean logout
  // with an explanatory toast.
  useEffect(() => {
    setUnauthHandler(() => logout('Your session expired. Please sign in again.'))
  }, [])

  // Restore the user profile on a fresh page load when a token already
  // exists in localStorage (e.g. after a refresh). Without this, `user`
  // stayed null forever after a refresh and the sidebar showed "Loading..."
  // indefinitely even though the session was valid.
  useEffect(() => {
    if (token && !user) {
      api('GET', '/auth/me').then(u => { if (u) setUser(u) }).catch(() => {})
    }
  }, [token])

  // Sidebar alert badge count. Previously setAlertCount was declared but
  // never called anywhere, so the badge never showed regardless of how
  // many open alerts existed.
  useEffect(() => {
    if (!token) return
    api('GET', '/alerts?expiry_days=30').then(a => { if (a) setAlertCount(a.total || 0) }).catch(() => {})
  }, [token, page])

  function login(tok, userObj) {
    loggedOutRef.current = false
    setToken(tok)
    setTokenState(tok)
    setUser(userObj)
  }

  function navigate(p, param = null) {
    setPage(p)
    setPageParam(param)
    window.scrollTo(0, 0)
  }

  function removeToast(id) {
    setToasts(t => t.filter(x => x.id !== id))
  }

  if (!token) {
    return (
      <div className="app">
        <Auth onLogin={login} toast={toast} />
        {toasts.map(t => <Toast key={t.id} {...t} onRemove={removeToast} />)}
      </div>
    )
  }

  function renderPage() {
    const props = { navigate, toast }
    switch (page) {
      case 'dashboard':    return <Dashboard {...props} />
      case 'vendors':      return <Vendors {...props} />
      case 'vendor-detail':return <VendorDetail id={pageParam} {...props} />
      case 'analysis':     return <AnalysisDetail id={pageParam} {...props} />
      case 'alerts':       return <Alerts {...props} />
      case 'report':       return <Report {...props} />
      default:             return <Dashboard {...props} />
    }
  }

  return (
    <div className="app">
      <div className="sidebar">
        <Sidebar
          page={page}
          navigate={navigate}
          user={user}
          alertCount={alertCount}
          onLogout={logout}
        />
      </div>
      <div className="content">
        {renderPage()}
      </div>
      {toasts.map(t => <Toast key={t.id} {...t} onRemove={removeToast} />)}
    </div>
  )
}
