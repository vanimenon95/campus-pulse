import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, Tabs, useLoad } from '../components/Ui'
import ClubManager from '../components/ClubManager'
import { OptimizerModal } from './EventDetail'
import { fmtDate, fmtLongDate, fmtRange, pct } from '../utils/format'

export default function CoordinatorDashboard() {
  const { user } = useAuth(); const toast = useToast()
  const { data, loading, error, reload } = useLoad(() => api.get('/coordinator/dashboard'))
  const [tab, setTab] = useState('events'); const [opt, setOpt] = useState(null); const [filter, setFilter] = useState('all')
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} retry={reload} />
  const t = data.totals
  const run = async (fn, ok) => { try { await fn(); toast.success(ok); reload() } catch (e) { toast.error(e.message) } }
  const publish = async (e) => {
    try { await api.post(`/events/${e.id}/publish`); toast.success('Event published.'); reload() }
    catch (err) {
      if (err.data?.needs_confirmation && window.confirm(`${err.message}\n\n${err.data.conflicts.map((c) => '• ' + c.message).join('\n')}\n\nPublish anyway?`)) {
        run(() => api.post(`/events/${e.id}/publish`, { force: true }), 'Event published.')
      } else if (!err.data?.needs_confirmation) toast.error(err.message)
    }
  }
  const cancel = (e) => window.confirm(`Cancel “${e.title}”? Registered students will be notified.`) && run(() => api.post(`/events/${e.id}/cancel`), 'Event cancelled.')
  const remove = (e) => window.confirm(`Delete “${e.title}” permanently?`) && run(() => api.del(`/events/${e.id}`), 'Event deleted.')
  const rows = data.events.filter((e) => filter === 'all' || e.status === filter || (filter === 'conflict' && e.conflict_count > 0))
  return (
    <>
      <div className="page-head"><div><h1>{user.role === 'admin' ? 'All clubs' : 'Coordinator'} dashboard</h1><p>Manage events, registrations and conflicts</p></div>
        <div className="actions"><Link className="btn primary" to="/coordinator/events/new">+ New event</Link><Link className="btn" to="/reports">Reports</Link></div></div>
      <div className="kpis"><div><b>{t.events}</b><span>Events</span></div><div><b>{t.published}</b><span>Published</span></div><div><b>{t.drafts}</b><span>Drafts</span></div><div><b>{t.registrations}</b><span>Registrations</span></div><div><b>{t.with_conflicts}</b><span>With conflicts</span></div></div>
      <Tabs value={tab} onChange={setTab} tabs={[['events', 'Events'], ['ai', `AI recommendations (${data.recommendations.length})`], ['clubs', 'Clubs & members']]} />
      {tab === 'events' && <>
        <div className="chips" style={{ marginBottom: 16 }}>{[['all', 'All'], ['published', 'Published'], ['draft', 'Drafts'], ['conflict', 'Conflicts']].map(([k, l]) => <button key={k} className={`chip ${filter === k ? 'on' : ''}`} onClick={() => setFilter(k)}>{l}</button>)}</div>
        {rows.length === 0 ? <Empty>No events here yet.</Empty> : <div className="panel tablewrap"><table><thead><tr><th>Event</th><th>When</th><th>Status</th><th>Reg.</th><th>Predicted</th><th>Conflicts</th><th>Actions</th></tr></thead><tbody>
          {rows.map((e) => (
            <tr key={e.id}><td><Link to={`/events/${e.id}`}><b>{e.title}</b></Link><div className="hint">{e.club_name} · {e.venue_name}</div></td><td>{fmtDate(e.start)}<div className="hint">{fmtRange(e.start, e.end)}</div></td>
              <td><span className={`badge ${e.status === 'published' ? 'ok' : e.status === 'draft' ? 'mu' : 'gray'}`}>{e.status}</span></td><td>{e.registered}/{e.capacity}</td>
              <td>{e.predicted_attendance}<div className="hint">{pct(e.predicted_rate)}{e.prediction_method === 'fallback_default' ? ' · fallback' : ''}</div></td>
              <td>{e.conflict_count ? <span className="badge">{e.conflict_count} · {e.affected_students} students</span> : <span className="hint">none</span>}</td>
              <td><div className="actions">
                {e.status !== 'cancelled' && <Link className="btn sm" to={`/coordinator/events/${e.id}/edit`}>Edit</Link>}
                {e.status === 'draft' && <button className="btn sm primary" onClick={() => publish(e)}>Publish</button>}
                {e.status === 'published' && <button className="btn sm" onClick={() => setOpt(e.id)}>Optimize</button>}
                {e.status === 'published' && new Date(e.start) < new Date() && <Link className="btn sm" to={`/coordinator/events/${e.id}/attendance`}>Attendance</Link>}
                {e.status === 'published' && <button className="btn sm danger" onClick={() => cancel(e)}>Cancel</button>}
                {e.status === 'draft' && <button className="btn sm danger" onClick={() => remove(e)}>Delete</button>}</div></td></tr>))}</tbody></table></div>}
      </>}
      {tab === 'ai' && (data.recommendations.length === 0 ? <Empty>No upcoming conflicts to fix. 🎉</Empty> : data.recommendations.map((r) => (
        <div className="notice" key={r.event_id}><span className="badge mu">Schedule optimizer</span><h3>{r.title}</h3>
          <p>{r.current_affected} students currently clash. Best alternative: <b>{fmtLongDate(r.best_start)}, {fmtRange(r.best_start, r.best_end)}</b> at {r.best_venue} — frees {r.students_saved} students and adds about +{r.improvement} expected attendees.</p>
          <button className="btn dark" onClick={() => setOpt(r.event_id)}>Review options</button></div>)))}
      {tab === 'clubs' && <ClubManager clubs={data.clubs} reload={reload} />}
      {opt && <OptimizerModal eventId={opt} onClose={() => setOpt(null)} onApplied={() => { setOpt(null); reload() }} />}
    </>
  )
}
