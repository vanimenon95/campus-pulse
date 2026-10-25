export const CAT_COLOR = { Tech: '#4f9080', Culture: '#e8a43c', Sports: '#c4402c', Academic: '#7a5980', Social: '#3f7fb0' }
export const catColor = (c) => CAT_COLOR[c] || '#4f9080'
const d = (s) => new Date(s)
export const fmtDate = (s) => d(s).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
export const fmtLongDate = (s) => d(s).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
export const fmtTime = (s) => d(s).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
export const fmtRange = (a, b) => `${fmtTime(a)} – ${fmtTime(b)}`
export const pct = (n) => (n == null ? '–' : `${Math.round(n * 100)}%`)
// <input type="datetime-local"> wants 2026-11-14T18:00
export const toLocalInput = (s) => { const x = d(s); const p = (n) => String(n).padStart(2, '0'); return `${x.getFullYear()}-${p(x.getMonth() + 1)}-${p(x.getDate())}T${p(x.getHours())}:${p(x.getMinutes())}` }
export const initials = (n = '') => n.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
