import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Bar, ErrorBox, Modal, Spinner, useLoad } from '../components/Ui'
import { catColor, fmtLongDate, fmtRange, fmtDate, fmtTime, pct } from '../utils/format'

export function OptimizerModal({ eventId, onClose, onApplied }) {
  const toast = useToast()
  const { data, loading, error } = useLoad(() => api.get(`/events/${eventId}/optimize`), [eventId])
  const [applying, setApplying] = useState(false)
  const apply = async (r) => {
    setApplying(true)
    try {
      const ev = (await api.get(`/events/${eventId}`)).event
      await api.put(`/events/${eventId}`, { title: ev.title, description: ev.description, category: ev.category,
        club_id: ev.club_id, venue_id: r.venue_id, capacity: ev.capacity, start: r.start, end: r.end })
      toast.success('Event moved to the suggested slot.'); onApplied?.()
    } catch (e) { toast.error(e.message) } finally { setApplying(false) }
  }
  return (
    <Modal title="Schedule optimizer" onClose={onClose}>
      {loading ? <Spinner /> : error ? <p className="err">{error}</p> : (
        <>
          <p className="hint">Now: {fmtLongDate(data.current.start)}, {fmtRange(data.current.start, data.current.end)} at {data.current.venue_name} —
            {' '}{data.current.affected_students} students clash · expected attendance {data.current.expected_attendance}</p>
          {data.recommendations.length === 0 && <p>{data.message}</p>}
          {data.recommendations.map((r, i) => (
            <div className="rec" key={i}>
              <b>{fmtLongDate(r.start)}, {fmtRange(r.start, r.end)}</b> · {r.venue_name}{!r.same_venue && ' (different venue)'}
              <div className="hint">{r.affected_students} clashing students ({r.students_saved >= 0 ? `${r.students_saved} fewer` : `${-r.students_saved} more`}) ·
                expected attendance {r.expected_attendance} (<b style={{ color: 'var(--mustard)' }}>+{r.improvement}</b>)</div>
              <button className="btn sm primary" disabled={applying} style={{ marginTop: 8 }} onClick={() => apply(r)}>Move event here</button>
            </div>
          ))}
          <p className="method">Time-of-day model: {data.time_model}. {data.searched_candidates} valid slots evaluated.</p>
        </>
      )}
      <div className="actions" style={{ marginTop: 18 }}><button className="btn sm" onClick={onClose}>Close</button></div>
    </Modal>
  )
}

export default function EventDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const [busy, setBusy] = useState(false)
  const [opt, setOpt] = useState(false)
  const { data, loading, error, reload } = useLoad(() => api.get(`/events/${id}`), [id, user?.id])
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} retry={reload} />
  const e = data.event
  const { prediction: p, overlap, conflicts } = e.insights
  const color = catColor(e.category)
  const finished = new Date(e.end) < new Date()
  const act = async (fn, ok) => {
    if (!user) { nav('/login', { state: { from: `/events/${id}` } }); return }
    setBusy(true)
    try { const r = await fn(); r?.warning ? toast.warn(r.warning) : toast.success(ok); reload() }
    catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }
  const worst = overlap.by_event.find((r) => r.shared_count > 0)
  return (
    <div className="grid2">
      <div>
        <div className="panel">
          <span className="tag" style={{ background: color }}>{e.club_name}</span>
          {e.status !== 'published' && <span className="badge gray" style={{ marginLeft: 10 }}>{e.status}</span>}
          <h1 style={{ fontSize: 40, margin: '16px 0 18px' }}>{e.title}</h1>
          <div className="meta" style={{ color: 'var(--ivory)' }}>
            <div><label className="lbl">Date</label><b>{fmtLongDate(e.start)}</b></div>
            <div><label className="lbl">Time</label><b>{fmtRange(e.start, e.end)}</b></div>
            <div><label className="lbl">Venue</label><b>{e.venue_name}</b></div>
          </div>
          {e.description && <p style={{ color: 'var(--muted)', marginBottom: 0 }}>{e.description}</p>}
        </div>

        <div className="metrics">
          <div><label>{finished ? 'Actual attendance' : 'Predicted attendance'}</label><b>{finished && e.attendance?.rate != null ? pct(e.attendance.rate) : pct(p.predicted_rate)}</b></div>
          <div><label>Registered</label><b>{e.registered}</b></div>
          <div><label>Venue capacity</label><b>{e.venue_capacity}</b></div>
        </div>

        {conflicts.length > 0 && (
          <div className="notice">
            <span className="badge">Conflict</span><h3>Scheduling notice from AI coordinator</h3>
            <p>
              {worst ? <>{worst.shared_count} registered students are also signed up for “{worst.title}”, which overlaps this event.</> : 'This event has scheduling problems.'}
              {' '}{overlap.affected_count > 0 && <>In total {overlap.affected_count} students ({pct(overlap.affected_pct)}) are affected. </>}
              {e.can_manage ? 'The schedule optimizer has a fix ready.' : 'Organizers have been alerted.'}
            </p>
            <ul style={{ margin: '0 0 14px', paddingLeft: 18, fontSize: 14 }}>{conflicts.map((c, i) => <li key={i}>{c.message}</li>)}</ul>
            {e.can_manage && <button className="btn dark" onClick={() => setOpt(true)}>See suggested time</button>}
          </div>
        )}
        {conflicts.length === 0 && <div className="panel" style={{ marginTop: 22 }}><span className="badge ok">Clear</span> No conflicts detected for this slot.</div>}

        {overlap.by_event.filter((r) => r.shared_count > 0).map((r) => (
          <div className="panel" key={r.event_id} style={{ marginTop: 22 }}>
            <h2>Students overlapping with {r.title.toLowerCase()}</h2>
            {r.students ? (
              <ul className="ol">{r.students.map((s, i) => <li key={s.id}><span className="n">{String(i + 1).padStart(2, '0')}</span><div><b>{s.name}</b><small>Also registered: {r.title}</small></div></li>)}</ul>
            ) : <p className="hint">{r.shared_count} students ({pct(r.pct_of_target)} of this event's registrations) are in both events. Names are visible to event organizers only.</p>}
          </div>
        ))}
      </div>

      <aside>
        <div className="panel">
          <h2>AI schedule confidence</h2>
          <Bar label="Attendance" value={p.predicted_rate} color="var(--teal)" />
          <Bar label="Venue fit" value={p.venue_fit} color="var(--mustard)" />
          <Bar label="Conflict-free" value={p.conflict_free} color="var(--red)" />
          <p className="method">
            <b>{p.method === 'historical' ? 'Historical model' : 'Fallback estimate'}</b> · confidence {p.confidence}. {p.explanation}
            {' '}Predicted turnout: ~{p.predicted_attendees} people.
          </p>
        </div>
        <div style={{ marginTop: 18 }} className="actions">
          {e.status === 'published' && !finished && (e.user_registered
            ? <button className="btn block" disabled={busy} onClick={() => act(() => api.del(`/events/${e.id}/register`), 'Registration cancelled.')}>✓ Registered — cancel</button>
            : <button className="btn primary block" style={{ padding: 18 }} disabled={busy || e.registered >= e.capacity}
                onClick={() => act(() => api.post(`/events/${e.id}/register`), "You're registered!")}>{e.registered >= e.capacity ? 'Event full' : 'Register for this event'}</button>)}
          {finished && e.attendance && <p className="hint">Recorded {e.attendance.present}/{e.attendance.recorded} present.</p>}
          {e.can_manage && <>
            <Link className="btn block" to={`/coordinator/events/${e.id}/edit`}>Edit event</Link>
            <Link className="btn block" to={`/coordinator/events/${e.id}/attendance`}>Attendance</Link>
          </>}
          <Link className="btn block" to={`/clubs/${e.club_id}`}>About {e.club_name}</Link>
        </div>
      </aside>
      {opt && <OptimizerModal eventId={e.id} onClose={() => setOpt(false)} onApplied={() => { setOpt(false); reload() }} />}
    </div>
  )
}
