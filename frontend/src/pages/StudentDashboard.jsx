import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, useLoad } from '../components/Ui'
import Ticket from '../components/Ticket'
import { fmtDate, fmtTime } from '../utils/format'

export default function StudentDashboard() {
  const { user } = useAuth(); const toast = useToast()
  const { data, loading, error, reload } = useLoad(() => api.get('/me/dashboard'))
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} retry={reload} />
  const d = data
  const markAll = async () => { await api.post('/me/notifications/read'); toast.success('All caught up.'); reload() }
  const cancel = async (e) => { try { await api.del(`/events/${e.id}/register`); toast.success('Registration cancelled.'); reload() } catch (err) { toast.error(err.message) } }
  const join = async (e) => { try { const r = await api.post(`/events/${e.id}/register`); r.warning ? toast.warn(r.warning) : toast.success("You're in!"); reload() } catch (err) { toast.error(err.message) } }
  return (
    <>
      <div className="page-head"><div><h1>Hi, {user.name.split(' ')[0]}</h1><p>Your clubs, events and notifications</p></div>
        <div className="actions"><Link className="btn" to="/calendar">Open calendar</Link><Link className="btn primary" to="/events">Find events</Link></div></div>
      <div className="kpis"><div><b>{d.clubs.length}</b><span>Clubs joined</span></div><div><b>{d.upcoming.length}</b><span>Upcoming events</span></div>
        <div><b>{d.my_clashes.length}</b><span>Schedule clashes</span></div><div><b>{d.unread}</b><span>Unread alerts</span></div></div>
      {d.my_clashes.map((c, i) => (
        <div className="notice" key={i}><span className="badge">Clash</span><h3>You can't attend both</h3>
          <p>“{c.a}” and “{c.b}” overlap. Cancel one registration to keep your week clear.</p>
          <Link className="btn" to={`/events/${c.a_id}`}>View first</Link> <Link className="btn" to={`/events/${c.b_id}`}>View second</Link></div>))}
      <div className="grid2" style={{ marginTop: 26 }}>
        <div>
          <h2 style={{ marginBottom: 16 }}>Registered events</h2>
          {d.upcoming.length === 0 ? <Empty>No upcoming registrations. <Link to="/events" style={{ color: 'var(--mustard)' }}>Browse events</Link></Empty> :
            <div style={{ display: 'grid', gap: 22 }}>{d.upcoming.map((e) => (
              <div key={e.id}><Ticket event={e} mini /><button className="btn sm danger" style={{ marginTop: 8 }} onClick={() => cancel(e)}>Cancel registration</button></div>))}</div>}
          {d.from_my_clubs.length > 0 && <><h2 style={{ margin: '34px 0 16px' }}>From your clubs</h2>
            <div style={{ display: 'grid', gap: 22 }}>{d.from_my_clubs.map((e) => <Ticket key={e.id} event={e} onJoin={join} />)}</div></>}
          {d.past.length > 0 && <><h2 style={{ margin: '34px 0 16px' }}>Past events</h2><div className="panel"><ul className="ol">{d.past.map((e) => <li key={e.id}><span className="n">{e.attended ? '✓' : '–'}</span><div><b>{e.title}</b><small>{fmtDate(e.start)} · {e.attended === true ? 'Attended' : e.attended === false ? 'Marked absent' : 'Not recorded'}</small></div></li>)}</ul></div></>}
        </div>
        <div>
          <div className="panel"><h2>My clubs</h2>{d.clubs.length === 0 ? <p className="hint">None yet. <Link to="/clubs" style={{ color: 'var(--mustard)' }}>Join one</Link></p> :
            <ul className="ol">{d.clubs.map((c) => <li key={c.id}><span className="n">{c.name[0]}</span><Link to={`/clubs/${c.id}`}><b>{c.name}</b><small>{c.member_count} members</small></Link></li>)}</ul>}</div>
          <div className="panel"><div style={{ display: 'flex', justifyContent: 'space-between' }}><h2>Notifications</h2>{d.unread > 0 && <button className="btn sm" onClick={markAll}>Mark all read</button>}</div>
            {d.notifications.length === 0 ? <p className="hint">Nothing yet.</p> : <ul className="ol">{d.notifications.slice(0, 8).map((n) => (
              <li key={n.id} style={{ opacity: n.is_read ? .6 : 1 }}><span className="n" style={n.kind === 'conflict' ? { color: 'var(--red)', borderColor: 'var(--red)' } : {}}>{n.kind === 'conflict' ? '!' : '•'}</span>
                <div>{n.event_id ? <Link to={`/events/${n.event_id}`}>{n.message}</Link> : n.message}<small>{fmtDate(n.created_at)} {fmtTime(n.created_at)}</small></div></li>))}</ul>}</div>
        </div>
      </div>
    </>
  )
}
