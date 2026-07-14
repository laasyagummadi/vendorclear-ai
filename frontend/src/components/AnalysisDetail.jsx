import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, fmtMoney, analysisBadgeClass, severityBadgeClass } from '../helpers.js'

export default function AnalysisDetail({ id, navigate, toast }) {
  const [analysis, setAnalysis] = useState(null)
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    api('GET', `/analyses/${id}`)
      .then(setAnalysis)
      .catch(e => { if (toast) toast('Error loading analysis: ' + (e?.message || e), 'error'); setAnalysis(null) })
  }, [id])

  if (!analysis) return (
    <div className="empty-state">
      <div className="spinner" style={{ width:24, height:24, borderWidth:3, margin:'48px auto' }} />
    </div>
  )

  const findings = analysis.findings || []
  const ef = analysis.extracted_fields || {}

  const fields = [
    ['Insured Name', analysis.insured_name || ef.insured_name],
    ['Insurer Name', analysis.insurer_name || ef.insurer_name],
    ['Policy Number', analysis.policy_number || ef.policy_number],
    ['Coverage Type', analysis.coverage_type || ef.coverage_type],
    ['GL Limit', fmtMoney(analysis.general_liability_limit_usd || ef.general_liability_limit_usd)],
    ['Workers Comp Limit', fmtMoney(analysis.workers_comp_limit_usd || ef.workers_comp_limit_usd)],
    ['Auto Liability Limit', fmtMoney(analysis.auto_liability_limit_usd || ef.auto_liability_limit_usd)],
    ['Effective Date', fmtDate(analysis.effective_date || ef.effective_date)],
    ['Expiry Date', fmtDate(analysis.expiry_date || ef.expiry_date)],
    ['Certificate Holder', analysis.certificate_holder || ef.certificate_holder],
    ['Additional Insured', analysis.additional_insured != null ? (analysis.additional_insured ? 'Yes' : 'No') : null],
    ['Cert Body', analysis.cert_body || ef.cert_body],
    ['Cert Type', analysis.cert_type || ef.cert_type],
    ['Cert Number', analysis.cert_number || ef.cert_number],
    ['Ownership %', analysis.ownership_pct != null ? analysis.ownership_pct + '%' : null],
  ].filter(([,v]) => v && v !== '—' && v !== null)

  return (
    <div>
      <div className="breadcrumb">
        <a onClick={() => navigate('vendors')}>Vendors</a>
        <span className="breadcrumb-sep">›</span>
        <a onClick={() => navigate('vendor-detail', analysis.vendor_id || '')}>Vendor</a>
        <span className="breadcrumb-sep">›</span>
        <span style={{ color:'#888' }}>Analysis</span>
      </div>

      <div className="page-header">
        <div>
          <div className="page-title">Document Analysis</div>
          <div className="flex gap-2 mt-1">
            <span className={`badge ${analysisBadgeClass(analysis.status)}`}>{analysis.status || '—'}</span>
            <span style={{ fontSize:12, color:'#444' }}>
              Confidence: {analysis.confidence_score ? (analysis.confidence_score*100).toFixed(0)+'%' : '—'}
            </span>
          </div>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:20 }}>
        <div className="card">
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
            <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em' }}>Extracted Fields</div>
            <button className="btn btn-ghost btn-sm" onClick={() => {
              const dataStr = JSON.stringify(analysis.extracted_fields || {}, null, 2)
              navigator.clipboard.writeText(dataStr)
                .then(() => toast && toast('Data copied to clipboard!', 'success'))
                .catch(() => toast && toast('Failed to copy', 'error'))
            }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight:6 }}><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
              Copy JSON
            </button>
          </div>
          {fields.length === 0
            ? <div style={{ color:'#333', fontSize:12 }}>No fields extracted.</div>
            : fields.map(([k,v]) => (
              <div key={k} className="detail-item" style={{ marginBottom:6 }}>
                <div className="detail-item-label">{k}</div>
                <div className="detail-item-val">{String(v)}</div>
              </div>
            ))
          }
        </div>

        <div className="card">
          <div style={{ fontSize:13, fontWeight:600, color:'#777', marginBottom:14, textTransform:'uppercase', letterSpacing:'.06em' }}>
            Compliance Findings ({findings.length})
          </div>
          {findings.length === 0
            ? <div style={{ color:'#333', fontSize:12, textAlign:'center', padding:'24px 0' }}>✓ No compliance issues found</div>
            : findings.map((f, i) => (
              <div key={i} className="finding-item">
                <div className="finding-sev"><span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity || '—'}</span></div>
                <div>
                  <div style={{ fontSize:12, fontWeight:600, color:'#bbb' }}>{f.rule_code || ''}</div>
                  <div style={{ fontSize:12, color:'#555', marginTop:2 }}>{f.message || ''}</div>
                </div>
              </div>
            ))
          }
        </div>
      </div>

      {analysis.raw_text && (
        <div className="card">
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
            <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em' }}>Raw OCR Text</div>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowRaw(!showRaw)}>
              {showRaw ? 'Hide Text' : 'View Raw Text'}
            </button>
          </div>
          {showRaw && (
            <pre style={{ fontSize:11, color:'#444', whiteSpace:'pre-wrap', wordBreak:'break-word', maxHeight:240, overflowY:'auto', lineHeight:1.6, borderTop:'1px solid #1a1a1a', paddingTop:12 }}>
              {analysis.raw_text.substring(0,2000)}{analysis.raw_text.length>2000?'\n…':''}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
