import { useState, useEffect } from 'react'
import { api } from '../api.js'

// Admin-only configuration panel.
// - Two tabs (Version 1 / Version 2), each showing every configurable setting.
// - Editing + Save, with an "Apply to existing vendors" checkbox (requirement 5).
// - A vendor list with a version selector to reassign vendors.
export default function AdminSettings({ toast }) {
  const [data, setData] = useState(null)          // { version_1, version_2, schema }
  const [activeVersion, setActiveVersion] = useState(1)
  const [draft, setDraft] = useState({})          // editable copy of the active version's settings
  const [applyExisting, setApplyExisting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function loadConfig() {
    setLoading(true)
    api('GET', '/config/versions')
      .then(res => {
        setData(res)
        setDraft({ ...(res[`version_${activeVersion}`] || {}) })
        setError('')
      })
      .catch(e => setError(e?.data?.detail || 'Could not load configuration (admin only).'))
      .finally(() => setLoading(false))
  }

  function loadVendors() {
    api('GET', '/vendors?page=1&page_size=100')
      .then(res => setVendors(res?.data || []))
      .catch(() => setVendors([]))
  }

  useEffect(() => { loadConfig(); loadVendors() }, [])
  useEffect(() => {
    if (data) setDraft({ ...(data[`version_${activeVersion}`] || {}) })
    setApplyExisting(false)
  }, [activeVersion, data])

  const schema = data?.schema || {}

  function setField(key, raw) {
    const type = schema[key]?.type
    let val = raw
    if (type === 'int') val = raw === '' ? '' : parseInt(raw, 10)
    else if (type === 'float') val = raw === '' ? '' : parseFloat(raw)
    else if (type === 'bool') val = raw
    setDraft(d => ({ ...d, [key]: val }))
  }

  async function save() {
    setSaving(true)
    try {
      const res = await api('PUT', `/config/versions/${activeVersion}`, {
        settings: draft,
        apply_to_existing: applyExisting,
      })
      const msg = applyExisting
        ? `Saved. Applied to ${res.vendors_updated} existing Version ${activeVersion} vendor(s).`
        : `Saved Version ${activeVersion} config. Existing vendors keep their current settings.`
      toast?.(msg, 'success')
      loadConfig(); loadVendors()
    } catch (e) {
      toast?.(e?.data?.detail || 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function assignVersion(vendorId, version) {
    try {
      await api('PUT', `/config/vendors/${vendorId}/version`, { version: Number(version) })
      toast?.(`Vendor assigned to Version ${version}.`, 'success')
      loadVendors()
    } catch (e) {
      toast?.(e?.data?.detail || 'Assignment failed', 'error')
    }
  }

  function fmtINR(n) {
    if (n == null || isNaN(n)) return '—'
    return '₹' + Number(n).toLocaleString('en-IN')
  }

  if (loading) return <div className="empty-state"><p>Loading configuration…</p></div>
  if (error) return (
    <div>
      <div className="page-header"><div><div className="page-title">Admin Settings</div></div></div>
      <div className="card"><div className="empty-state"><p>{error}</p></div></div>
    </div>
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Admin Settings</div>
          <div className="page-sub">Configure version-specific compliance settings · admin only</div>
        </div>
      </div>

      {/* Version tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[1, 2].map(v => (
          <button
            key={v}
            className={`btn btn-sm ${activeVersion === v ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveVersion(v)}
          >
            Version {v}
            <span style={{ marginLeft: 8, opacity: 0.7, fontSize: 11 }}>
              {fmtINR(data?.[`version_${v}`]?.compliance_compensation_inr)}
            </span>
          </button>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 700, marginBottom: 4 }}>Version {activeVersion} Configuration</div>
        <div style={{ fontSize: 12, color: '#605e5c', marginBottom: 16 }}>
          Edit any setting below. New vendors assigned to this version always receive these values.
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {Object.entries(schema).map(([key, meta]) => (
            <div key={key}>
              <label style={{ fontSize: 12, color: '#605e5c', display: 'block', marginBottom: 4 }}>
                {meta.label}
              </label>
              {meta.type === 'bool' ? (
                <select
                  className="input"
                  value={draft[key] ? 'true' : 'false'}
                  onChange={e => setField(key, e.target.value === 'true')}
                >
                  <option value="true">Required</option>
                  <option value="false">Not required</option>
                </select>
              ) : (
                <input
                  className="input"
                  type="number"
                  step={meta.type === 'float' ? '0.01' : '1'}
                  value={draft[key] ?? ''}
                  onChange={e => setField(key, e.target.value)}
                />
              )}
              <div style={{ fontSize: 11, color: '#605e5c', marginTop: 3 }}>{meta.help}</div>
            </div>
          ))}
        </div>

        {/* Apply-to-existing checkbox (requirement 5) */}
        <div style={{ marginTop: 20, padding: 14, background: '#f3f2f1', borderRadius: 8, border: '1px solid #e1dfdd' }}>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={applyExisting}
              onChange={e => setApplyExisting(e.target.checked)}
              style={{ marginTop: 2 }}
            />
            <span>
              <span style={{ fontWeight: 600, fontSize: 13 }}>
                Apply these changes to existing Version {activeVersion} vendors
              </span>
              <span style={{ display: 'block', fontSize: 11, color: '#605e5c', marginTop: 2 }}>
                If unchecked, existing vendors keep their current settings; only newly assigned
                vendors get these values.
              </span>
            </span>
          </label>
        </div>

        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save Configuration'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={loadConfig} disabled={saving}>
            Reset
          </button>
        </div>
      </div>

      {/* Vendor version assignment */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 16px', fontWeight: 700, borderBottom: '1px solid #e1dfdd' }}>
          Vendor Version Assignments
        </div>
        {vendors.length === 0
          ? <div className="empty-state"><p>No vendors yet.</p></div>
          : <table className="tbl">
              <thead><tr><th>Vendor</th><th>Current Version</th><th>Compensation</th><th>Reassign</th></tr></thead>
              <tbody>
                {vendors.map(v => (
                  <tr key={v.id}>
                    <td style={{ fontWeight: 600 }}>{v.name}</td>
                    <td>Version {v.assigned_version || 1}</td>
                    <td>{fmtINR(v.effective_config?.compliance_compensation_inr)}</td>
                    <td>
                      <select
                        className="input"
                        style={{ width: 120, padding: '4px 8px' }}
                        value={v.assigned_version || 1}
                        onChange={e => assignVersion(v.id, e.target.value)}
                      >
                        <option value={1}>Version 1</option>
                        <option value={2}>Version 2</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
        }
      </div>
    </div>
  )
}
