import { useState, useRef } from 'react'
import { api } from '../../api.js'

// NOTE on fixes made here:
// - Posted to `/api/v1/vendors/${vendorId}/documents/upload` (relative URL,
//   extra "/upload" segment) instead of the registered route
//   `POST /api/v1/vendors/{vendor_id}/documents`. That path never matched
//   any backend route, so uploads 404'd every single time — the core
//   "upload & analyze" feature of this app never worked at all. Fixed to
//   use the shared api.js helper (correct absolute host + correct path).
// - Sent form field `doc_type` but the backend reads `doc_type_hint`
//   (default "AUTO"), and only understands "COI" / "DIVERSITY_CERT" hints
//   — none of the granular insurance-line options below map to anything
//   the compliance engine recognizes. Simplified the dropdown to the two
//   document types the backend actually classifies, plus auto-detect.
export default function UploadModal({ vendorId, vendorName, onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [docType, setDocType] = useState('AUTO')
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const inputRef = useRef()

  const DOC_TYPES = [
    { value:'AUTO', label:'Auto-detect' },
    { value:'COI', label:'Certificate of Insurance' },
    { value:'DIVERSITY_CERT', label:'Diversity Certificate' },
  ]

  function handleDrop(e) {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  async function submit(e) {
    e.preventDefault()
    if (!file) { setErr('Please select a file'); return }
    setLoading(true); setErr('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('doc_type_hint', docType)
      const data = await api('POST', `/vendors/${vendorId}/documents`, fd, true)
      if (!data) { setErr('Upload failed'); return }
      onUploaded(data)
    } catch (ex) {
      setErr(ex?.data?.error || ex?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const fmtSize = b => b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`

  return (
    <div className="modal-overlay" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">Upload Document</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={submit}>
          <div className="modal-body">
            {err && <div className="alert alert-error" style={{ marginBottom:16 }}>{err}</div>}
            <div className="form-group">
              <label className="form-label">Vendor</label>
              <input className="form-input" value={vendorName} disabled />
            </div>
            <div className="form-group">
              <label className="form-label">Document Type</label>
              <select className="form-input" value={docType} onChange={e=>setDocType(e.target.value)}>
                {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div
              className={`upload-zone${dragOver ? ' dragover' : ''}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={e=>{e.preventDefault();setDragOver(true)}}
              onDragLeave={()=>setDragOver(false)}
              onDrop={handleDrop}
            >
              {file ? (
                <div>
                  <div className="upload-icon">📄</div>
                  <div style={{ fontWeight:600 }}>{file.name}</div>
                  <div style={{ color:'#555', fontSize:12, marginTop:4 }}>{fmtSize(file.size)}</div>
                  <div style={{ color:'#666', fontSize:11, marginTop:6 }}>Click to change</div>
                </div>
              ) : (
                <div>
                  <div className="upload-icon">⬆</div>
                  <div>Drop a file here or <span style={{ color:'#aaa', textDecoration:'underline', cursor:'pointer' }}>browse</span></div>
                  <div style={{ color:'#555', fontSize:12, marginTop:6 }}>PDF, PNG, JPG, TIFF, DOCX — max 20 MB</div>
                </div>
              )}
              <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.docx" style={{ display:'none' }}
                onChange={e => e.target.files[0] && setFile(e.target.files[0])} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !file}>
              {loading ? 'Uploading…' : 'Upload & Analyze'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
