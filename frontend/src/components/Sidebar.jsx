export default function Sidebar({ page, navigate, user, alertCount, onLogout }) {
  // Module 4/5 — navigation is gated by role so each user only sees the
  // sections their permissions actually allow.
  const perms = user?.permissions || []
  const isVendorRole = user?.role === 'VENDOR'
  const canViewAllVendors = !isVendorRole
  const canViewReports = !isVendorRole
  const isAdmin = user?.role === 'ADMIN' || user?.is_admin
  return (
    <aside className="sidebar">
      <div className="brand-logo">
        <div className="brand-dot">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="brand-name">VendorClear AI</div>
          <div className="brand-tag">Vendor Intelligence</div>
        </div>
      </div>

      <div className="nav-section">Main</div>
      <div className={`nav-item ${page === 'dashboard' ? 'active' : ''}`} onClick={() => navigate('dashboard')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
        Dashboard
      </div>
      {canViewAllVendors && (
      <div className={`nav-item ${page === 'vendors' || page === 'vendor-detail' ? 'active' : ''}`} onClick={() => navigate('vendors')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        Vendors
      </div>
      )}

      <div className={`nav-item ${page === 'upload' ? 'active' : ''}`} onClick={() => navigate('upload')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        Upload
      </div>

      {canViewReports && (<>
      <div className="nav-sep" />
      <div className="nav-section">Intelligence</div>
      <div className={`nav-item ${page === 'alerts' ? 'active' : ''}`} onClick={() => navigate('alerts')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>
        </svg>
        Alerts
        {alertCount > 0 && (
          <span style={{ marginLeft: 'auto', background: '#f87171', color: '#000', borderRadius: 20, fontSize: 10, fontWeight: 700, padding: '1px 7px' }}>
            {alertCount}
          </span>
        )}
      </div>
      <div className={`nav-item ${page === 'report' ? 'active' : ''}`} onClick={() => navigate('report')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        Compliance Report
      </div>

      <div className={`nav-item ${page === 'approvals' ? 'active' : ''}`} onClick={() => navigate('approvals')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
        </svg>
        Approvals
      </div>

      {(user?.role === 'ADMIN' || user?.role === 'AUDITOR' || user?.is_admin) && (
      <div className={`nav-item ${page === 'audit' ? 'active' : ''}`} onClick={() => navigate('audit')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/>
        </svg>
        Audit Trail
      </div>
      )}
      </>)}

      {(user?.role === 'ADMIN' || user?.is_admin) && (
        <>
          <div className="nav-section">Admin</div>
          <div className={`nav-item ${page === 'admin-settings' ? 'active' : ''}`} onClick={() => navigate('admin-settings')}>
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            Settings
          </div>
        </>
      )}

      <div style={{ flex: 1 }} />
      <div className="nav-sep" />
      <div style={{ padding: 10, background: '#f3f2f1', borderRadius: 8, marginBottom: 8 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#1b1a19' }}>{user?.full_name || 'Loading...'}</div>
        <div style={{ fontSize: 11, color: '#a19f9d' }}>{user?.email || ''}</div>
      </div>
      <div className="nav-item" onClick={onLogout}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        Sign Out
      </div>
    </aside>
  )
}
