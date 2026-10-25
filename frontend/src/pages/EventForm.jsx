import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Field, Spinner, useLoad } from '../components/Ui'
import { toLocalInput } from '../utils/format'

const CATS = ['Tech', 'Culture', 'Sports', 'Academic', 'Social']
export default function EventForm() {
  const { id } = useParams(); const nav = useNavigate(); const toast = useToast()
  const lists = useLoad(async () => ({ clubs: (await api.get('/coordinator/dashboard')).clubs, venues: (await api.get('/venues')).venues, ev: id ? (await api.get(`/events/${id}`)).event : null }), [id])
  const [f, setF] = useState({ title: '', description: '', category: 'Tech', club_id: '', venue_id: '', start: '', end: '', capacity: '' })
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [check, setCheck] = useState(null)

  useEffect(() => {
    if (!lists.data) return
    const { clubs, venues, ev } = lists.data
    if (ev) setF({ title: ev.title, description: ev.description || '', category: ev.category, club_id: ev.club_id, venue_id: ev.venue_id, start: toLocalInput(ev.start), end: toLocalInput(ev.end), capacity: ev.capacity || '' })
    else setF((x) => ({ ...x, club_id: clubs[0]?.id || '', venue_id: venues[0]?.id || '' }))
  }, [lists.data])

  // live conflict check (Conflict Detector) whenever venue/time changes
  useEffect(() => {
    if (!f.venue_id || !f.start || !f.end || f.end <= f.start) return setCheck(null)
    const h = setTimeout(() => api.post('/venues/check', { venue_id: +f.venue_id, start: f.start, end: f.end, event_id: id ? +id : null, expected: f.capacity ? +f.capacity : null }).then(setCheck).catch(() => setCheck(null)), 350)
    return () => clearTimeout(h)
  }, [f.venue_id, f.start, f.end, f.capacity, id])

  if (lists.loading) return <Spinner />
  if (lists.error) return <p className="err">{lists.error}</p>
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    if (f.title.trim().length < 3) return setErr('Title must be at least 3 characters.')
    if (!f.start || !f.end) return setErr('Choose a start and end time.')
    if (f.end <= f.start) return setErr('End time must be after the start time.')
    if (f.start.slice(0, 10) !== f.end.slice(0, 10)) return setErr('Events must start and end on the same day.')
    setBusy(true)
    try {
      const body = { ...f, club_id: +f.club_id, venue_id: +f.venue_id, capacity: f.capacity ? +f.capacity : null }
      id ? await api.put(`/events/${id}`, body) : await api.post('/events', body)
      toast.success(id ? 'Event updated.' : 'Draft saved. Publish it from your dashboard.'); nav('/coordinator')
    } catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }
  const venue = lists.data.venues.find((v) => v.id === +f.venue_id)
  return (
    <>
      <div className="page-head"><h1>{id ? 'Edit event' : 'Create event'}</h1></div>
      <div className="grid2">
        <form className="form wide panel" onSubmit={submit} noValidate>
          <Field label="Title"><input className="input" value={f.title} onChange={set('title')} /></Field>
          <div className="f2"><Field label="Club"><select className="select" value={f.club_id} onChange={set('club_id')}>{lists.data.clubs.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
            <Field label="Category"><select className="select" value={f.category} onChange={set('category')}>{CATS.map((c) => <option key={c}>{c}</option>)}</select></Field></div>
          <div className="f2"><Field label="Venue"><select className="select" value={f.venue_id} onChange={set('venue_id')}>{lists.data.venues.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.capacity})</option>)}</select></Field>
            <Field label="Registration cap" hint={venue ? `Venue holds ${venue.capacity}` : ''}><input className="input" type="number" min="1" value={f.capacity} onChange={set('capacity')} /></Field></div>
          <div className="f2"><Field label="Starts"><input className="input" type="datetime-local" value={f.start} onChange={set('start')} /></Field>
            <Field label="Ends"><input className="input" type="datetime-local" value={f.end} onChange={set('end')} /></Field></div>
          <Field label="Description"><textarea className="textarea" value={f.description} onChange={set('description')} /></Field>
          {err && <div className="err" role="alert">{err}</div>}
          <div className="actions"><button className="btn primary" disabled={busy}>{busy ? 'Saving…' : id ? 'Save changes' : 'Save as draft'}</button><button type="button" className="btn" onClick={() => nav(-1)}>Cancel</button></div>
        </form>
        <div className="panel"><h2>Conflict detector</h2>
          {!check ? <p className="hint">Pick a venue and time to run a live check.</p> : check.conflicts.length === 0 ? <p><span className="badge ok">Clear</span> Venue is free and within opening hours.</p> :
            <ul className="ol">{check.conflicts.map((c, i) => <li key={i}><span className={`badge ${c.severity === 'high' ? '' : 'mu'}`}>{c.severity}</span><div>{c.message}</div></li>)}</ul>}
          {check && !check.ok && <p className="err">High-severity conflicts block publishing.</p>}
        </div>
      </div>
    </>
  )
}
