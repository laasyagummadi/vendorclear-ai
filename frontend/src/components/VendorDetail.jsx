import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, fmtSize, isExpiring, statusBadgeClass, riskBadgeClass, docTypeBadgeClass, docStatusBadgeClass } from '../helpers.js'
import EditVendorModal from './modals/EditVendorModal.jsx'
import UploadModal from './modals/UploadModal.jsx'

export default function VendorDetail({ id, navigate, toast }) {
  const [vendor, setVendor] = useState(null)
  const [docs, setDocs] = useState([])
  const [score, setScore] = useState(null)
  const [showEdit, setShowEdit] = useState(false)
  const [showUpload, setShowUpload] = useState(false)

  function load() {
    Promise.all([
      api('GET', `/vendors/${id}`),
      api('GET', `/vendors/${id}/documents`),
      api('GET', `/dashboard/vendors/${id}/score`),
    ]).then(([v, d, s]) => { setVendor(v); setDocs(d || []); setScore(s) }).catch((e) => { toast('Error loading vendor: ' + JSON.stringify(e), 'error') })
  }

  useEffect(() => { load() }, [id])

  if (!vendor) return (
    <div className="empty-state">
      <div className="spinner" style={{ width:24, height:24, borderWidth:3, margin:'48px auto' }} />
    </div>
  )

  const grade = score?.grade || '?'
  const totalScore = score?.total_score ?? null
  const gradeColor = grade==='A'?'#4ade80':grade==='B'?'#86efac':grade==='C'?'#fbbf24':grade==='D'?'#fb923c':'#f87171'

  async function loadDocAnalysis(docId) {
    try {
      const analyses = await api('GET', `/vendors/${id}/documents/${docId}/analyses`)
      if (analyses && analyses.length > 0) navigate('analysis', analyses[0].id)
      else toast('No analysis available for this document yet.', 'info')
    } catch(e) { toast('Could not load analysis.', 'error') }
  }

  return (
    <div>
      <div className="breadcrumb">
        <a onClick={() => navigate('vendors')}>Vendors</a>
        <span className="breadcrumb-sep">›</span>
        <span style={{ color:'#888' }}>{vendor.name}</span>
      </div>

      <div className="page-header">
        <div>
          <div className="page-title">{vendor.name}</div>
          <div className="flex gap-2 mt-1">
            <span className={`badge ${statusBadgeClass(vendor.status)}`}>{vendor.status || '—'}</span>
            <span className={`badge ${riskBadgeClass(vendor.risk_tier)}`}>{vendor.risk_tier || '—'}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-ghost btn-sm" onClick={() => setShowUpload(true)}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            Upload Document
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowEdit(true)}>Edit</button>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 320px', gap:20, marginBottom:24 }}>
        <div className="card">
          <div style={{ fontSize:13, fontWeight:600, color:'#777', marginBottom:14, textTransform:'uppercase', letterSpacing:'.06em' }}>Vendor Info</div>
          <div className="detail-grid">
            {[['Contact', vendor.contact_name],['Email', vendor.email],['Phone', vendor.phone],
              ['City / State', [vendor.city,vendor.state].filter(Boolean).join(', ')],
              ['GL Expiry', fmtDate(vendor.gl_expiry)],['WC Expiry', fmtDate(vendor.wc_expiry)]
            ].map(([label, val]) => (
              <div key={label} className="detail-item">
                <div className="detail-item-label">{label}</div>
                <div className="detail-item-val" style={{ color: (label.includes('Expiry') && isExpiring(label==='GL Expiry'?vendor.gl_expiry:vendor.wc_expiry)) ? '#f87171' : undefined }}>
                  {val || '—'}
                </div>
              </div>
            ))}
            <div className="detail-item" style={{ gridColumn:'span 2' }}>
              <div className="detail-item-label">Diversity Types</div>
              <div className="detail-item-val">{(vendor.diversity_types||[]).length ? vendor.diversity_types.join(', ') : '—'}</div>
            </div>
          </div>
        </div>

        <div className="card" style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', textAlign:'center' }}>
          <div style={{ fontSize:12, color:'#444', textTransform:'uppercase', letterSpacing:'.06em', marginBottom:14 }}>Compliance Score</div>
          <div style={{ fontSize:64, fontWeight:800, letterSpacing:-3, color:gradeColor, lineHeight:1 }}>{grade}</div>
          {totalScore !== null && <div style={{ fontSize:14, color:'#555', marginTop:6 }}>{totalScore}/100</div>}
          {score?.breakdown && (
            <div style={{ marginTop:16, width:'100%' }}>
              {Object.entries(score.breakdown).map(([k,v]) => (
                <div key={k} style={{ display:'flex', justifyContent:'space-between', fontSize:11, marginBottom:6 }}>
                  <span style={{ color:'#444' }}>{k.replace(/_/g,' ')}</span>
                  <span style={{ color:'#666' }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'16px 20px', borderBottom:'1px solid #111' }}>
          <div style={{ fontSize:14, fontWeight:600 }}>Documents ({docs.length})</div>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowUpload(true)}>+ Upload</button>
        </div>
        {docs.length === 0 ? (
          <div className="empty-state"><div className="icon">📄</div><p>No documents uploaded yet.</p></div>
        ) : (
          <table className="tbl">
            <thead><tr><th>Filename</th><th>Type</th><th>Status</th><th>Size</th><th>Uploaded</th><th></th></tr></thead>
            <tbody>
              {docs.map(d => (
                <tr key={d.id} onClick={() => loadDocAnalysis(d.id)}>
                  <td><div style={{ fontWeight:500 }}>{d.filename}</div></td>
                  <td><span className={`badge ${docTypeBadgeClass(d.document_type)}`}>{d.document_type || '—'}</span></td>
                  <td><span className={`badge ${docStatusBadgeClass(d.status)}`}>{d.status || '—'}</span></td>
                  <td style={{ color:'#555', fontSize:12 }}>{fmtSize(d.file_size_bytes)}</td>
                  <td style={{ color:'#555', fontSize:12 }}>{fmtDate(d.created_at)}</td>
                  <td style={{ textAlign:'right' }}><span style={{ color:'#333', fontSize:18, padding:'0 8px' }}>›</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showEdit && <EditVendorModal id={id} onClose={() => setShowEdit(false)} onSaved={() => { setShowEdit(false); toast('Vendor updated!','success'); load() }} />}
      {showUpload && <UploadModal vendorId={id} vendorName={vendor.name} onClose={() => setShowUpload(false)} onUploaded={() => { setShowUpload(false); toast('Document uploaded and analyzed!','success'); load() }} />}
    </div>
  )
}
