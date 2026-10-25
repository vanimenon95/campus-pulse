import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, useLoad } from '../components/Ui'
import Ticket from '../components/Ticket'

const WHEN = [['upcoming', 'Upcoming'], ['0', 'This week'], ['1', 'Next week']]
export default function Events() {
  const { user } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')
  const [when, setWhen] = useState('upcoming')
  const [busy, setBusy] = useState(false)
  const [onlyConflicts, setOnlyConflicts] = useState(false)

  const params = new URLSearchParams()
  if (when === 'upcoming') params.set('upcoming', '1'); else params.set('week', when)
  if (cat) params.set('category', cat)
  if (q.trim()) params.set('q', q.trim())
  const { data, loading, error, reload } = useLoad(() => api.get('/events?' + params), [cat, q, when, user?.id])

  const join = async (e) => {
    if (!user) { nav('/login', { state: { from: '/events' } }); return }
    setBusy(true)
    try {
      const r = await api.post(`/events/${e.id}/register`)
      r.warning ? toast.warn(r.warning) : toast.success(`You're in! See you at ${e.title}.`)
      reload()
    } catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }
  let events = data?.events || []
  if (onlyConflicts) events = events.filter((e) => e.flags?.affected_students > 0 || e.flags?.venue_conflict)
  const cats = ['', ...(data?.categories || ['Tech', 'Culture', 'Sports', 'Academic', 'Social'])]
  return (
    <>
      <div className="page-head">
        <div><h1>This week's lineup</h1><p>Curated and conflict-checked across all clubs</p></div>
        <div className="chips">{cats.map((c) => <button key={c} className={`chip ${cat === c ? 'on' : ''}`} onClick={() => setCat(c)}>{c || 'For you'}</button>)}</div>
      </div>
      <div className="toolbar">
        <input className="input" placeholder="Search events or clubs…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <div className="chips">{WHEN.map(([k, l]) => <button key={k} className={`chip ${when === k ? 'on' : ''}`} onClick={() => setWhen(k)}>{l}</button>)}</div>
        <label className="hint" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={onlyConflicts} onChange={(e) => setOnlyConflicts(e.target.checked)} /> Show conflicts only
        </label>
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} retry={reload} /> :
        events.length === 0 ? <Empty>No events match. Try another filter.</Empty> :
          <div className="feed">{events.map((e) => <Ticket key={e.id} event={e} onJoin={join} busy={busy} />)}</div>}
    </>
  )
}
