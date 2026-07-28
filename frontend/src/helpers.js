export function esc(s) {
  return String(s || '')
}

export function fmtDate(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }
  catch (e) { return String(d) }
}

export function fmtSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

export function fmtMoney(v) {
  if (v == null) return '—'
  return '$' + Number(v).toLocaleString('en-US')
}

export function isExpiring(dateStr, days = 30) {
  if (!dateStr) return false
  const diff = (new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24)
  return diff >= 0 && diff <= days
}

export function statusBadgeClass(s) {
  const map = { ACTIVE: 'badge-green', COMPLIANT: 'badge-green', NEEDS_REVIEW: 'badge-yellow', PENDING: 'badge-gray', INACTIVE: 'badge-gray', SUSPENDED: 'badge-red', NON_COMPLIANT: 'badge-red' }
  return map[s] || 'badge-gray'
}

export function riskBadgeClass(r) {
  const map = { LOW: 'badge-green', MEDIUM: 'badge-yellow', HIGH: 'badge-red', CRITICAL: 'badge-red', UNKNOWN: 'badge-gray' }
  return map[r] || 'badge-gray'
}

export function docTypeBadgeClass(t) {
  const map = { COI: 'badge-blue', DIVERSITY_CERT: 'badge-purple', UNKNOWN: 'badge-gray' }
  return map[t] || 'badge-gray'
}

export function docStatusBadgeClass(s) {
  const map = { PROCESSED: 'badge-green', PROCESSING: 'badge-yellow', PENDING: 'badge-gray', FAILED: 'badge-red' }
  return map[s] || 'badge-gray'
}

export function analysisBadgeClass(s) {
  const map = { COMPLIANT: 'badge-green', NEEDS_REVIEW: 'badge-yellow', NON_COMPLIANT: 'badge-red' }
  return map[s] || 'badge-gray'
}

export function severityBadgeClass(s) {
  const map = { CRITICAL: 'badge-red', HIGH: 'badge-red', MEDIUM: 'badge-yellow', LOW: 'badge-blue' }
  return map[s] || 'badge-gray'
}
