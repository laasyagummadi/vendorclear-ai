import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { analysisBadgeClass } from '../helpers.js'

export default function Upload({ navigate, toast }) {
  const [vendors, setVendors] = useState([])
  const [vendorId, setVendorId] = useState('')
  const [newVendorName, setNewVendorName] = useState('')
  const [docTypeHint, setDocTypeHint] = useState('AUTO')
  const [file, setFile] = useState(null)
  const [recentAnalyses, setRecentAnalyses] = useState([])
  
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressText, setProgressText] = useState('')
  const [uploadError, setUploadError] = useState('')
  
  const fileInputRef = useRef(null)
  const dragRef = useRef(null)

  useEffect(() => {
    api('GET', '/vendors?page_size=100')
      .then(res => {
        const list = res?.items || res?.data || (Array.isArray(res) ? res : [])
        setVendors(list)
      })
      .catch(() => setVendors([]))
      
    api('GET', '/analyses/recent?limit=5')
      .then(res => setRecentAnalyses(res || []))
      .catch(err => console.error("Failed to fetch recent analyses", err))
  }, [])

  const handleDragOver = (e) => {
    e.preventDefault()
    if (dragRef.current) {
      dragRef.current.style.borderColor = 'rgba(255,255,255,.4)'
      dragRef.current.style.background = 'rgba(255,255,255,.03)'
    }
  }

  const handleDragLeave = () => {
    if (dragRef.current) {
      dragRef.current.style.borderColor = 'rgba(255,255,255,.12)'
      dragRef.current.style.background = 'transparent'
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    handleDragLeave()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const triggerUpload = async () => {
    if (!vendorId) {
      setUploadError('Please select a vendor')
      return
    }
    if (vendorId === '__new__' && !newVendorName.trim()) {
      setUploadError('Please enter a name for the new vendor')
      return
    }
    if (!file) {
      setUploadError('Please select a document file')
      return
    }

    setUploadError('')
    setLoading(true)
    setProgress(10)
    setProgressText('Preparing upload...')

    try {
      let activeVendorId = vendorId

      if (vendorId === '__new__') {
        setProgress(35)
        setProgressText('Creating new vendor...')
        const vendorRes = await api('POST', '/vendors', {
          name: newVendorName.trim()
        })
        if (vendorRes && vendorRes.id) {
          activeVendorId = vendorRes.id
          toast(`Vendor "${newVendorName.trim()}" created successfully`, 'success')
        } else {
          throw new Error('Failed to create new vendor')
        }
      }

      setProgress(60)
      setProgressText('Uploading file...')

      const formData = new FormData()
      formData.append('file', file)
      formData.append('doc_type_hint', docTypeHint)

      setProgress(75)
      setProgressText('Analyzing document with Gemini AI...')

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
      setProgressText('Retrieving AI compliance results...')
      toast('Document uploaded and analyzed successfully!', 'success')
      
      const docId = data.document?.id
      if (docId) {
        setProgress(92)
        setProgressText('Fetching final findings...')
        // Small delay to ensure backend DB commit is fully visible
        await new Promise(r => setTimeout(r, 600))
        const analyses = await api('GET', `/vendors/${activeVendorId}/documents/${docId}/analyses`)
        if (analyses && analyses.length > 0) {
          setProgress(100)
          navigate('analysis', analyses[0].id)
        } else {
          setProgress(100)
          toast('Document saved — check vendor details for analysis status.', 'info')
          navigate('vendor-detail', activeVendorId)
        }
      } else {
        setProgress(100)
        setProgressText('Complete!')
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

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Upload Center</div>
          <div className="page-sub">Upload Certificates of Insurance or Diversity Certs for immediate compliance evaluation</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          {/* Step 1 Form */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ display: 'inline-flex', width: 22, height: 22, borderRadius: '50%', background: '#fff', color: '#000', fontSize: 11, fontWeight: 800, alignItems: 'center', justifyContent: 'center' }}>1</span>
              <span>Select Vendor & Document Details</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label className="form-label">Vendor Association</label>
                <select 
                  className="form-input" 
                  value={vendorId} 
                  onChange={e => {
                    setVendorId(e.target.value)
                    setUploadError('')
                  }}
                  style={{ width: '100%', background: '#111', cursor: 'pointer' }}
                >
                  <option value="">-- Choose vendor --</option>
                  <option value="__new__">➕ Create New Vendor...</option>
                  {vendors.map(v => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>

                {vendorId === '__new__' && (
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="Enter new vendor name..." 
                    value={newVendorName} 
                    onChange={e => setNewVendorName(e.target.value)}
                    style={{ width: '100%', marginTop: 8, borderColor: '#3b82f6', animation: 'fadeIn 0.2s ease' }}
                  />
                )}
              </div>

              <div>
                <label className="form-label">Document Type Hint</label>
                <select 
                  className="form-input" 
                  value={docTypeHint} 
                  onChange={e => setDocTypeHint(e.target.value)}
                  style={{ width: '100%', background: '#111', cursor: 'pointer' }}
                >
                  <option value="AUTO">Auto Detect (AI Assisted)</option>
                  <option value="COI">Certificate of Insurance (COI)</option>
                  <option value="DIVERSITY_CERT">Diversity Certificate</option>
                </select>
              </div>
            </div>
            <div style={{ marginTop: 12, fontSize: 11, color: '#444' }}>
              💡 If the vendor is not in the directory yet, choose "Create New Vendor..." to add them to the database automatically during upload.
            </div>
          </div>

          {/* Step 2 File Drop */}
          <div 
            ref={dragRef}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed rgba(255,255,255,.12)',
              borderRadius: 14,
              padding: '48px 24px',
              textAlign: 'center',
              background: 'transparent',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 180
            }}
          >
            <div style={{ fontSize: 36, marginBottom: 12 }}>📤</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#fff', marginBottom: 4 }}>
              {file ? file.name : 'Drop document file here or click to browse'}
            </div>
            <div style={{ fontSize: 12, color: '#444' }}>
              {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB · Click to change` : 'Accepts PDF, PNG, JPG, JPEG up to 20MB'}
            </div>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept=".pdf,.png,.jpg,.jpeg" 
              style={{ display: 'none' }} 
            />
          </div>

          {/* Actions & Progress */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {uploadError && (
              <div style={{ background: 'rgba(248,113,113,.1)', border: '1px solid #f87171', color: '#f87171', padding: '12px 16px', borderRadius: 8, fontSize: 13, marginBottom: 8 }}>
                <strong>Upload Error:</strong> {uploadError}
              </div>
            )}
            
            {progress > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#aaa', fontWeight: 600 }}>
                  <span className="pulsing-text">{progressText}</span>
                  <span>{progress}%</span>
                </div>
                <div style={{ width: '100%', background: '#222', height: 8, borderRadius: 4, overflow: 'hidden', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)' }}>
                  <div style={{ height: '100%', background: 'linear-gradient(90deg, #3b82f6, #4ade80)', width: `${progress}%`, transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }} />
                </div>
              </div>
            )}
            
            <button 
              className="btn btn-primary" 
              style={{ justifyContent: 'center', padding: '12px 24px', fontWeight: 600 }}
              onClick={triggerUpload}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ marginRight: 8 }} />
                  Processing Document with AI...
                </>
              ) : 'Run Upload & AI Compliance Check'}
            </button>
            
            {uploadError && (
              <div style={{ color: '#f87171', fontSize: 12, textAlign: 'center', marginTop: 6, animation: 'fadeIn 0.2s ease' }}>
                ⚠️ {uploadError}
              </div>
            )}
          </div>

        </div>

        {/* Instructions Pane */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#777', textTransform: 'uppercase', letterSpacing: '.06em' }}>Supported Classes</div>
          
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ fontSize: 18 }}>🛡️</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#e0e0e0' }}>Insurance Policies (COI)</div>
              <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>Extracts General Liability, Auto, and Workers Comp limits and checks requirements.</div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ fontSize: 18 }}>🏷️</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#e0e0e0' }}>Diversity Certifications</div>
              <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>Verifies MBE, WBE, DBE, HUBZone classifications, expiration status, and ownership percent.</div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ fontSize: 18 }}>⚡</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#e0e0e0' }}>Real-time OCR & AI</div>
              <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>Image files are parsed via pytesseract OCR, then analyzed in seconds with Gemini 1.5 Flash.</div>
            </div>
          </div>
        </div>
      </div>

      {/* Previously Analyzed Section */}
      <div style={{ marginTop: 40 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#fff', marginBottom: 16 }}>Previously Analyzed Documents</div>
        {recentAnalyses.length === 0 ? (
          <div className="card" style={{ padding: '24px', textAlign: 'center', color: '#555' }}>
            No recent analyses found.
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Vendor</th>
                  <th>Status</th>
                  <th>Extracted Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentAnalyses.map(a => (
                  <tr key={a.id} onClick={() => navigate('analysis', a.id)}>
                    <td style={{ color: '#e0e0e0', fontWeight: 600 }}>{vendors.find(v => v.id === a.vendor_id)?.name || 'Unknown Vendor'}</td>
                    <td>
                      <span className={`badge ${analysisBadgeClass(a.status)}`}>
                        {a.status}
                      </span>
                    </td>
                    <td style={{ color: '#666' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}><span style={{ color: '#333', fontSize: 18 }}>›</span></td>
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
