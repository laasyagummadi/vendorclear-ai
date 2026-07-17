export default function Sidebar({ page, navigate, user, alertCount, onLogout }) {
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
      <div className={`nav-item ${page === 'vendors' || page === 'vendor-detail' ? 'active' : ''}`} onClick={() => navigate('vendors')}>
        <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        Vendors
      </div>

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

      <div style={{ flex: 1 }} />
      <div className="nav-sep" />
      <div style={{ padding: 10, background: '#111', borderRadius: 8, marginBottom: 8 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc' }}>{user?.full_name || 'Loading...'}</div>
        <div style={{ fontSize: 11, color: '#444' }}>{user?.email || ''}</div>
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
