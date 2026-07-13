import { useState, useCallback } from 'react'
import { getToken, setToken, api } from './api.js'
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

  function login(tok, userObj) {
    setToken(tok)
    setTokenState(tok)
    setUser(userObj)
  }

  function logout() {
    setToken('')
    setTokenState('')
    setUser(null)
    setPage('dashboard')
    setPageParam(null)
  }

  function navigate(p, param = null) {
    setPage(p)
    setPageParam(param)
    window.scrollTo(0, 0)
  }

  function toast(msg, type = 'success') {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
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
      case 'vendor-detail':return <VendorDetail vendorId={pageParam} {...props} />
      case 'analysis':     return <AnalysisDetail analysisId={pageParam} {...props} />
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
