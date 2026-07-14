import { useState, useRef } from 'react'
import { api } from '../../api.js'

export default function UploadModal({ vendorId, vendorName, onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [docType, setDocType] = useState('general_liability')
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const inputRef = useRef()

  const DOC_TYPES = [
    { value:'general_liability', label:'General Liability' },
    { value:'workers_comp', label:"Workers' Comp" },
    { value:'professional_liability', label:'Professional Liability' },
    { value:'auto_liability', label:'Auto Liability' },
    { value:'umbrella', label:'Umbrella / Excess' },
    { value:'cyber_liability', label:'Cyber Liability' },
    { value:'contract', label:'Contract' },
    { value:'w9', label:'W-9' },
    { value:'soc2', label:'SOC 2 Report' },
    { value:'other', label:'Other' },
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
      if (!data) throw new Error('Upload failed')
      onUploaded(data)
    } catch (ex) {
      const msg = ex?.data?.detail || ex?.data?.error || ex?.message || 'Upload failed'
      setErr(msg)
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
                  <div style={{ color:'#555', fontSize:12, marginTop:6 }}>PDF, PNG, JPG, TIFF — max 20 MB</div>
                </div>
              )}
              <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif" style={{ display:'none' }}
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
