import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { analysisBadgeClass } from '../helpers.js'

// ── Processing stage tracker (Module 6) ────────────────────
const STAGES = ['Queued', 'Uploading', 'OCR', 'AI Analysis', 'Compliance', 'Done']

function ProcessingStage({ stage, status }) {
  const idx = STAGES.indexOf(stage)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
      {STAGES.map((s, i) => {
        const done = status === 'completed' || i < idx
        const active = i === idx && status !== 'completed' && status !== 'failed'
        const failed = status === 'failed' && i === idx
        const color = done ? '#107c10' : active ? '#0078d4' : failed ? '#a4262c' : '#d0cece'
        return (
          <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{
              width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: done ? '#dff6dd' : active ? '#deecf9' : failed ? '#fde7e9' : '#f3f2f1',
              border: `2px solid ${color}`, fontSize: 9, fontWeight: 700, color, position: 'relative'
            }}>
              {active && <span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5, borderTopColor: '#0078d4', borderColor: '#deecf9' }} />}
              {done && '✓'}
              {failed && '✕'}
              {!active && !done && !failed && i + 1}
            </div>
            {i < STAGES.length - 1 && (
              <div style={{ width: 24, height: 2, background: done ? '#107c10' : '#e1dfdd' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function Upload({ navigate, toast, user }) {
  const canUpload = user?.role !== 'AUDITOR'
  const [vendors, setVendors] = useState([])
  const [vendorId, setVendorId] = useState('')
  const [newVendorName, setNewVendorName] = useState('')
  const [docTypeHint, setDocTypeHint] = useState('AUTO')
  const [recentAnalyses, setRecentAnalyses] = useState([])

  // Single file upload
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressText, setProgressText] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [duplicateWarning, setDuplicateWarning] = useState(null)

  // Bulk upload (Module 5)
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkFiles, setBulkFiles] = useState([])
  const [bulkResults, setBulkResults] = useState([])
  const [bulkLoading, setBulkLoading] = useState(false)

  const fileInputRef = useRef(null)
  const bulkInputRef = useRef(null)
  const dragRef = useRef(null)

  useEffect(() => {
    api('GET', '/vendors?page=1&page_size=100')
      .then(res => setVendors(res?.data || res?.items || (Array.isArray(res) ? res : [])))
      .catch(() => setVendors([]))

    api('GET', '/analyses/recent?limit=5')
      .then(res => setRecentAnalyses(res || []))
      .catch(() => {})
  }, [])

  // ── Drag & drop ─────────────────────────────────────────
  const handleDragOver = (e) => {
    e.preventDefault()
    if (dragRef.current) {
      dragRef.current.style.borderColor = '#0078d4'
      dragRef.current.style.background = '#f0f7ff'
    }
  }
  const handleDragLeave = () => {
    if (dragRef.current) {
      dragRef.current.style.borderColor = '#c8c6c4'
      dragRef.current.style.background = '#faf9f8'
    }
  }
  const handleDrop = (e) => {
    e.preventDefault()
    handleDragLeave()
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0])
      setDuplicateWarning(null)
    }
  }
  const handleFileChange = (e) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
      setDuplicateWarning(null)
    }
  }

  // ── Single upload ────────────────────────────────────────
  const triggerUpload = async (skipDupCheck = false) => {
    if (!vendorId) { setUploadError('Please select a vendor'); return }
    if (vendorId === '__new__' && !newVendorName.trim()) { setUploadError('Please enter a name for the new vendor'); return }
    if (!file) { setUploadError('Please select a document file'); return }

    setUploadError('')
    setLoading(true)
    setProgress(10)
    setProgressText('Preparing upload...')

    try {
      let activeVendorId = vendorId

      if (vendorId === '__new__') {
        setProgress(25)
        setProgressText('Creating new vendor...')
        const vendorRes = await api('POST', '/vendors', { name: newVendorName.trim() })
        if (vendorRes?.id) {
          activeVendorId = vendorRes.id
          toast(`Vendor "${newVendorName.trim()}" created`, 'success')
        } else {
          throw new Error('Failed to create new vendor')
        }
      }

      // Module 7: Duplicate detection
      if (!skipDupCheck) {
        setProgress(35)
        setProgressText('Checking for duplicates...')
        const dupForm = new FormData()
        dupForm.append('file', file)
        try {
          const dupCheck = await api('POST', `/vendors/${activeVendorId}/documents/duplicate-check`, dupForm, true)
          if (dupCheck?.duplicate) {
            setDuplicateWarning({
              filename: dupCheck.existing_filename,
              uploadedAt: dupCheck.uploaded_at,
              vendorId: activeVendorId,
            })
            setLoading(false)
            setProgress(0)
            setProgressText('')
            return
          }
        } catch {
          // Duplicate check failure is non-fatal — proceed
        }
      }

      setDuplicateWarning(null)
      setProgress(55)
      setProgressText('Uploading & classifying document...')

      const formData = new FormData()
      formData.append('file', file)
      formData.append('doc_type_hint', docTypeHint)

      setProgress(70)
      setProgressText('AI analysis in progress (Gemini)...')

      let data
      try {
        data = await api('POST', `/vendors/${activeVendorId}/documents`, formData, true)
      } catch (err) {
        const errData = err?.data || {}
        let msg = errData.error || errData.detail || 'Upload failed'
        if (errData.details && Array.isArray(errData.details)) {
          msg = errData.details.map(d => `${d.field}: ${d.message}`).join(', ')
        }
        throw new Error(msg)
      }

      if (!data) throw new Error('Upload failed — no response from server')

      setProgress(90)
      setProgressText('Retrieving compliance results...')
      toast('Document uploaded and analyzed!', 'success')

      const docId = data.document?.id
      if (docId) {
        await new Promise(r => setTimeout(r, 600))
        const analyses = await api('GET', `/vendors/${activeVendorId}/documents/${docId}/analyses`)
        if (analyses?.length > 0) {
          setProgress(100)
          navigate('analysis', analyses[0].id)
        } else {
          setProgress(100)
          navigate('vendor-detail', activeVendorId)
        }
      } else {
        setProgress(100)
        navigate('vendors')
      }
    } catch (err) {
      setUploadError(err.message || 'An error occurred during upload')
      setProgress(0)
      setProgressText('')
    } finally {
      setLoading(false)
    }
  }

  // ── Bulk upload (Module 5) ───────────────────────────────
  const triggerBulkUpload = async (force = false) => {
    if (!vendorId || vendorId === '__new__') { setUploadError('Please select an existing vendor for bulk upload'); return }
    if (bulkFiles.length === 0) { setUploadError('Please select files for bulk upload'); return }

    setUploadError('')
    setBulkLoading(true)
    setBulkResults([])

    // Initialize result placeholders with queued state
    const init = bulkFiles.map(f => ({
      filename: f.name, status: 'queued', stage: 'Queued',
      compliance_status: null, analysis_id: null, error: null, duplicate: false
    }))
    setBulkResults(init)

    const formData = new FormData()
    bulkFiles.forEach(f => formData.append('files', f))
    formData.append('doc_type_hint', docTypeHint)
    formData.append('force', force ? 'true' : 'false')

    // Update all to uploading
    setBulkResults(prev => prev.map(r => ({ ...r, status: 'uploading', stage: 'Uploading' })))

    try {
      const res = await api('POST', `/vendors/${vendorId}/documents/bulk-upload`, formData, true)
      if (res?.results) {
        setBulkResults(res.results.map(r => ({
          filename: r.filename,
          status: r.status,
          stage: r.status === 'completed' ? 'Done' : r.status === 'failed' ? 'AI Analysis' : r.status === 'duplicate' ? 'Done' : 'Done',
          compliance_status: r.compliance_status,
          analysis_id: r.analysis_id,
          document_type: r.document_type,
          error: r.error,
          duplicate: r.duplicate,
        })))
        const s = res.summary
        toast(`Bulk complete: ${s.completed} done · ${s.failed} failed · ${s.duplicates} duplicates`, s.failed > 0 ? 'error' : 'success')
      }
    } catch (err) {
      setUploadError(err?.data?.detail || 'Bulk upload failed')
      setBulkResults(prev => prev.map(r => ({ ...r, status: 'failed', stage: 'AI Analysis' })))
    } finally {
      setBulkLoading(false)
    }
  }

  const statusColor = (s) => s === 'completed' ? '#107c10' : s === 'failed' ? '#a4262c' : s === 'duplicate' ? '#97600a' : '#0078d4'
  const statusBg = (s) => s === 'completed' ? '#dff6dd' : s === 'failed' ? '#fde7e9' : s === 'duplicate' ? '#fff4ce' : '#deecf9'

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Upload Center</div>
          <div className="page-sub">Upload Certificates of Insurance or Diversity Certs for AI compliance evaluation</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn ${bulkMode ? 'btn-ghost' : 'btn-primary'} btn-sm`}
            onClick={() => { setBulkMode(false); setBulkResults([]) }}
          >Single File</button>
          <button
            className={`btn ${bulkMode ? 'btn-primary' : 'btn-ghost'} btn-sm`}
            onClick={() => { setBulkMode(true); setFile(null); setDuplicateWarning(null) }}
          >📦 Bulk Upload</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20, alignItems: 'start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Vendor + Doc type selector */}
          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1b1a19', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ display: 'inline-flex', width: 22, height: 22, borderRadius: '50%', background: '#0078d4', color: '#fff', fontSize: 11, fontWeight: 800, alignItems: 'center', justifyContent: 'center' }}>1</span>
              Select Vendor & Document Details
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label className="form-label">Vendor</label>
                <select
                  className="form-input"
                  value={vendorId}
                  onChange={e => { setVendorId(e.target.value); setUploadError('') }}
                >
                  <option value="">-- Choose vendor --</option>
                  {!bulkMode && <option value="__new__">➕ Create New Vendor...</option>}
                  {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
                {vendorId === '__new__' && (
                  <input
                    type="text" className="form-input"
                    placeholder="Enter new vendor name..."
                    value={newVendorName}
                    onChange={e => setNewVendorName(e.target.value)}
                    style={{ marginTop: 8, borderColor: '#0078d4' }}
                  />
                )}
              </div>
              <div>
                <label className="form-label">Document Type Hint</label>
                <select className="form-input" value={docTypeHint} onChange={e => setDocTypeHint(e.target.value)}>
                  <option value="AUTO">🤖 Auto Detect (AI Assisted)</option>
                  <option value="COI">Certificate of Insurance (COI)</option>
                  <option value="DIVERSITY_CERT">Diversity Certificate</option>
                </select>
              </div>
            </div>
          </div>

          {/* Single file upload */}
          {!bulkMode && (
            <>
              <div
                ref={dragRef}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: '2px dashed #c8c6c4',
                  borderRadius: 12, padding: '40px 24px',
                  textAlign: 'center', background: '#faf9f8', cursor: 'pointer',
                  transition: 'all 0.2s ease', display: 'flex',
                  flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 160
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 10 }}>📤</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1b1a19', marginBottom: 4 }}>
                  {file ? file.name : 'Drop document here or click to browse'}
                </div>
                <div style={{ fontSize: 12, color: '#605e5c' }}>
                  {file ? `${(file.size / 1048576).toFixed(2)} MB · Click to change` : 'PDF, PNG, JPG, JPEG up to 20MB'}
                </div>
                <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf,.png,.jpg,.jpeg" style={{ display: 'none' }} />
              </div>

              {/* Duplicate warning (Module 7) */}
              {duplicateWarning && (
                <div style={{ background: '#fff4ce', border: '1px solid #fbbf24', borderRadius: 8, padding: '14px 16px' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#97600a', marginBottom: 6 }}>
                    ⚠ Duplicate Document Detected
                  </div>
                  <div style={{ fontSize: 12, color: '#605e5c' }}>
                    This exact file was previously uploaded as <strong>"{duplicateWarning.filename}"</strong>.
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => setDuplicateWarning(null)}>Cancel</button>
                    <button className="btn btn-sm" style={{ background: '#97600a', color: '#fff' }} onClick={() => triggerUpload(true)}>
                      Upload Anyway
                    </button>
                  </div>
                </div>
              )}

              {/* Progress */}
              {progress > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#605e5c', fontWeight: 600 }}>
                    <span>{progressText}</span>
                    <span>{progress}%</span>
                  </div>
                  <div style={{ width: '100%', background: '#e1dfdd', height: 6, borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ height: '100%', background: 'linear-gradient(90deg, #0078d4, #107c10)', width: `${progress}%`, transition: 'width 0.4s ease' }} />
                  </div>
                </div>
              )}

              {uploadError && (
                <div style={{ background: '#fde7e9', border: '1px solid #f5c2c7', borderRadius: 8, padding: '12px 14px', fontSize: 13, color: '#a4262c' }}>
                  ⚠ {uploadError}
                </div>
              )}

              <button
                className="btn btn-primary"
                style={{ justifyContent: 'center', padding: '12px 24px' }}
                onClick={() => triggerUpload(false)}
                disabled={loading || !canUpload}
              >
                {loading ? <><span className="spinner" style={{ marginRight: 8 }} />Processing with AI...</> : !canUpload ? 'Read-only (Auditor)' : 'Upload & Run AI Compliance Check'}
              </button>
            </>
          )}

          {/* Bulk upload (Module 5) */}
          {bulkMode && (
            <>
              <div
                onClick={() => bulkInputRef.current?.click()}
                style={{
                  border: '2px dashed #c8c6c4', borderRadius: 12, padding: '32px 24px',
                  textAlign: 'center', background: '#faf9f8', cursor: 'pointer', transition: 'all .2s ease'
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1b1a19', marginBottom: 4 }}>
                  {bulkFiles.length > 0 ? `${bulkFiles.length} file(s) selected` : 'Click to select multiple files'}
                </div>
                <div style={{ fontSize: 12, color: '#605e5c' }}>PDF, PNG, JPG up to 50 files per batch</div>
                <input
                  type="file" ref={bulkInputRef} multiple
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={e => setBulkFiles(Array.from(e.target.files || []))}
                  style={{ display: 'none' }}
                />
              </div>

              {bulkFiles.length > 0 && (
                <div className="card" style={{ padding: 0, overflow: 'hidden', maxHeight: 200, overflowY: 'auto' }}>
                  {bulkFiles.map((f, i) => (
                    <div key={i} style={{ padding: '8px 16px', borderBottom: '1px solid #f3f2f1', display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: '#1b1a19' }}>{f.name}</span>
                      <span style={{ color: '#a19f9d' }}>{(f.size / 1048576).toFixed(2)} MB</span>
                    </div>
                  ))}
                </div>
              )}

              {uploadError && (
                <div style={{ background: '#fde7e9', border: '1px solid #f5c2c7', borderRadius: 8, padding: '12px 14px', fontSize: 13, color: '#a4262c' }}>
                  ⚠ {uploadError}
                </div>
              )}

              <button
                className="btn btn-primary"
                style={{ justifyContent: 'center', padding: '12px 24px' }}
                onClick={() => triggerBulkUpload(false)}
                disabled={bulkLoading || !canUpload || bulkFiles.length === 0}
              >
                {bulkLoading ? <><span className="spinner" style={{ marginRight: 8 }} />Processing batch...</> : `Upload ${bulkFiles.length} File(s) in Bulk`}
              </button>
              
              {bulkResults.some(r => r.duplicate) && (
                <button
                  className="btn"
                  style={{ background: '#97600a', color: '#fff', justifyContent: 'center', padding: '12px 24px', marginTop: '8px' }}
                  onClick={() => triggerBulkUpload(true)}
                  disabled={bulkLoading || !canUpload}
                >
                  Force Upload Duplicates
                </button>
              )}

              {/* Processing queue display (Module 6) */}
              {bulkResults.length > 0 && (
                <div className="card" style={{ padding: 0 }}>
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid #e1dfdd', fontSize: 12, fontWeight: 600, color: '#605e5c', textTransform: 'uppercase', letterSpacing: '.06em' }}>
                    Processing Queue
                  </div>
                  {bulkResults.map((r, i) => (
                    <div key={i} style={{ padding: '12px 16px', borderBottom: i < bulkResults.length - 1 ? '1px solid #f3f2f1' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#1b1a19', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {r.filename}
                        </div>
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                          textTransform: 'uppercase', letterSpacing: '.04em',
                          background: statusBg(r.status), color: statusColor(r.status)
                        }}>
                          {r.status}
                        </span>
                      </div>
                      <ProcessingStage stage={r.stage} status={r.status} />
                      {r.error && <div style={{ fontSize: 11, color: '#a4262c', marginTop: 4 }}>⚠ {r.error}</div>}
                      {r.compliance_status && (
                        <div style={{ fontSize: 11, color: '#605e5c', marginTop: 4 }}>
                          {r.document_type} · {r.compliance_status}
                          {r.analysis_id && (
                            <span
                              style={{ color: '#0078d4', cursor: 'pointer', marginLeft: 8 }}
                              onClick={() => navigate('analysis', r.analysis_id)}
                            >View →</span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Info pane */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="card">
            <div style={{ fontSize: 11, fontWeight: 600, color: '#605e5c', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>
              Supported Classes
            </div>
            {[
              ['🛡️', 'Insurance Policies (COI)', 'Extracts GL, Auto, Workers Comp limits and checks requirements.'],
              ['🏷️', 'Diversity Certifications', 'Verifies MBE, WBE, DBE, HUBZone classifications and ownership %.'],
              ['🤖', 'Auto Classification', 'AI predicts document type — no manual selection needed.'],
              ['🔍', 'Duplicate Detection', 'SHA-256 hash check prevents duplicate processing.'],
            ].map(([icon, title, desc]) => (
              <div key={title} style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
                <div style={{ fontSize: 18, flexShrink: 0 }}>{icon}</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1b1a19' }}>{title}</div>
                  <div style={{ fontSize: 11, color: '#605e5c', marginTop: 2 }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Pipeline stages info */}
          <div className="card">
            <div style={{ fontSize: 11, fontWeight: 600, color: '#605e5c', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>
              Processing Pipeline
            </div>
            {STAGES.map((s, i) => (
              <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#deecf9', color: '#0078d4', fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  {i + 1}
                </div>
                <div style={{ fontSize: 12, color: '#1b1a19' }}>{s}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Previously Analyzed */}
      <div style={{ marginTop: 32 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1b1a19', marginBottom: 14 }}>Previously Analyzed Documents</div>
        {recentAnalyses.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', color: '#605e5c', padding: '24px' }}>No recent analyses found.</div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="tbl">
              <thead>
                <tr><th>Vendor</th><th>Status</th><th>Date</th><th></th></tr>
              </thead>
              <tbody>
                {recentAnalyses.map(a => (
                  <tr key={a.id} onClick={() => navigate('analysis', a.id)}>
                    <td style={{ fontWeight: 600 }}>{vendors.find(v => v.id === a.vendor_id)?.name || 'Unknown Vendor'}</td>
                    <td><span className={`badge ${analysisBadgeClass(a.status)}`}>{a.status}</span></td>
                    <td style={{ color: '#605e5c', fontSize: 12 }}>{new Date(a.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}><span style={{ color: '#a19f9d', fontSize: 18 }}>›</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
