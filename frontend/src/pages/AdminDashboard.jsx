import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Field, Modal, Spinner, Tabs, useLoad } from '../components/Ui'
import { CreateClubForm } from '../components/ClubManager'
import { fmtDate, fmtRange } from '../utils/format'

function Users() {
  const { user: me } = useAuth(); const toast = useToast(); const [q, setQ] = useState('')
  const { data, loading, error, reload } = useLoad(() => api.get('/admin/users?q=' + encodeURIComponent(q)), [q])
  const run = async (fn, ok) => { try { const r = await fn(); toast.success(r?.message || ok); reload() } catch (e) { toast.error(e.message) } }
  return (<>
    <div className="toolbar"><input className="input" placeholder="Search users…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
    {loading ? <Spinner /> : error ? <ErrorBox message={error} retry={reload} /> : <div className="panel tablewrap"><table><thead><tr><th>User</th><th>Role</th><th>Status</th><th /></tr></thead><tbody>{data.users.map((u) => (
      <tr key={u.id}><td><b>{u.name}</b><div className="hint">{u.email}</div></td>
        <td><select className="select" style={{ width: 140 }} value={u.role} disabled={u.id === me.id} onChange={(e) => run(() => api.put(`/admin/users/${u.id}`, { role: e.target.value }), 'Role updated.')}>{['student', 'coordinator', 'admin'].map((r) => <option key={r}>{r}</option>)}</select></td>
        <td><button className={`sw ${u.is_active ? 'on' : ''}`} disabled={u.id === me.id} aria-label="Toggle active" onClick={() => run(() => api.put(`/admin/users/${u.id}`, { is_active: !u.is_active }), 'Status updated.')} /></td>
        <td>{u.id !== me.id && <button className="btn sm danger" onClick={() => window.confirm(`Delete ${u.name}?`) && run(() => api.del(`/admin/users/${u.id}`), 'User deleted.')}>Delete</button>}</td></tr>))}</tbody></table></div>}
  </>)
}

function VenueForm({ venue, onClose, onSaved }) {
  const toast = useToast()
  const [f, setF] = useState(venue ? { ...venue, facilities: venue.facilities.join(', ') } : { name: '', location: '', capacity: 50, facilities: '', open_time: '08:00', close_time: '21:00' })
  const [err, setErr] = useState(''); const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const save = async (e) => {
    e.preventDefault(); setErr('')
    try { const body = { ...f, capacity: +f.capacity, facilities: f.facilities.split(',').map((s) => s.trim()).filter(Boolean) }
      venue ? await api.put(`/venues/${venue.id}`, body) : await api.post('/venues', body); toast.success('Venue saved.'); onSaved() } catch (e2) { setErr(e2.message) }
  }
  return (<Modal title={venue ? 'Edit venue' : 'Add venue'} onClose={onClose}><form className="form wide" onSubmit={save} noValidate>
    <Field label="Name"><input className="input" value={f.name} onChange={set('name')} /></Field><Field label="Location"><input className="input" value={f.location || ''} onChange={set('location')} /></Field>
    <div className="f2"><Field label="Capacity"><input className="input" type="number" min="1" value={f.capacity} onChange={set('capacity')} /></Field><Field label="Facilities (comma separated)"><input className="input" value={f.facilities} onChange={set('facilities')} /></Field></div>
    <div className="f2"><Field label="Opens"><input className="input" type="time" value={f.open_time} onChange={set('open_time')} /></Field><Field label="Closes"><input className="input" type="time" value={f.close_time} onChange={set('close_time')} /></Field></div>
    {err && <div className="err">{err}</div>}<div className="actions"><button className="btn primary">Save</button><button type="button" className="btn" onClick={onClose}>Cancel</button></div></form></Modal>)
}

function BlackoutForm({ venue, onClose, onSaved }) {
  const toast = useToast(); const [f, setF] = useState({ start: '', end: '', reason: 'Maintenance' }); const [err, setErr] = useState('')
  const save = async (e) => { e.preventDefault(); try { await api.post(`/venues/${venue.id}/blackouts`, f); toast.success('Venue blocked.'); onSaved() } catch (e2) { setErr(e2.message) } }
  return (<Modal title={`Block ${venue.name}`} onClose={onClose}><form className="form wide" onSubmit={save}>
    <div className="f2"><Field label="From"><input className="input" type="datetime-local" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></Field><Field label="Until"><input className="input" type="datetime-local" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></Field></div>
    <Field label="Reason"><input className="input" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
    {err && <div className="err">{err}</div>}<div className="actions"><button className="btn primary">Block</button><button type="button" className="btn" onClick={onClose}>Cancel</button></div></form></Modal>)
}

function Venues() {
  const toast = useToast(); const { data, loading, error, reload } = useLoad(() => api.get('/venues')); const [edit, setEdit] = useState(null); const [block, setBlock] = useState(null)
  if (loading) return <Spinner />; if (error) return <ErrorBox message={error} retry={reload} />
  const del = async (v) => { if (!window.confirm(`Delete ${v.name}?`)) return; try { await api.del(`/venues/${v.id}`); toast.success('Venue deleted.'); reload() } catch (e) { toast.error(e.message) } }
  return (<>
    <button className="btn primary" style={{ marginBottom: 16 }} onClick={() => setEdit('new')}>+ Add venue</button>
    <div className="panel tablewrap"><table><thead><tr><th>Venue</th><th>Capacity</th><th>Hours</th><th>Facilities</th><th /></tr></thead><tbody>{data.venues.map((v) => (
      <tr key={v.id}><td><b>{v.name}</b><div className="hint">{v.location}</div></td><td>{v.capacity}</td><td>{v.open_time}–{v.close_time}</td><td>{v.facilities.join(', ')}</td>
        <td><div className="actions"><button className="btn sm" onClick={() => setEdit(v)}>Edit</button><button className="btn sm" onClick={() => setBlock(v)}>Block time</button><button className="btn sm danger" onClick={() => del(v)}>Delete</button></div></td></tr>))}</tbody></table></div>
    {edit && <VenueForm venue={edit === 'new' ? null : edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload() }} />}
    {block && <BlackoutForm venue={block} onClose={() => setBlock(null)} onSaved={() => { setBlock(null); reload() }} />}
  </>)
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('users'); const toast = useToast()
  const ov = useLoad(() => api.get('/admin/overview'))
  const clubs = useLoad(() => api.get('/admin/clubs'), [tab])
  const events = useLoad(() => api.get('/admin/events'), [tab])
  const conflicts = useLoad(() => api.get('/ai/conflicts'), [tab])
  const toggleClub = async (c) => { try { await api.put(`/clubs/${c.id}`, { is_active: !c.is_active }); toast.success('Club updated.'); clubs.reload() } catch (e) { toast.error(e.message) } }
  const o = ov.data
  return (<>
    <div className="page-head"><div><h1>Admin dashboard</h1><p>Users, clubs, venues, events and reports</p></div><div className="actions"><Link className="btn" to="/reports">Reports</Link><Link className="btn" to="/coordinator">All events</Link></div></div>
    {o && <div className="kpis">{[['users', 'Users'], ['clubs', 'Clubs'], ['venues', 'Venues'], ['events', 'Events'], ['published', 'Published'], ['registrations', 'Registrations']].map(([k, l]) => <div key={k}><b>{o[k]}</b><span>{l}</span></div>)}</div>}
    <Tabs value={tab} onChange={setTab} tabs={[['users', 'Users'], ['clubs', 'Clubs'], ['venues', 'Venues'], ['events', 'Events'], ['conflicts', 'AI conflicts']]} />
    {tab === 'users' && <Users />}
    {tab === 'clubs' && <div className="grid2"><div className="panel tablewrap"><table><thead><tr><th>Club</th><th>Coordinator</th><th>Members</th><th>Active</th></tr></thead><tbody>{(clubs.data?.clubs || []).map((c) => <tr key={c.id}><td><Link to={`/clubs/${c.id}`}><b>{c.name}</b></Link></td><td>{c.coordinator_name}</td><td>{c.member_count}</td><td><button className={`sw ${c.is_active ? 'on' : ''}`} aria-label="Toggle active" onClick={() => toggleClub(c)} /></td></tr>)}</tbody></table></div>
      <div className="panel"><h2>Create a club</h2><CreateClubForm onDone={clubs.reload} /></div></div>}
    {tab === 'venues' && <Venues />}
    {tab === 'events' && (events.loading ? <Spinner /> : <div className="panel tablewrap"><table><thead><tr><th>Event</th><th>Club</th><th>When</th><th>Status</th><th>Reg.</th></tr></thead><tbody>{events.data.events.map((e) => <tr key={e.id}><td><Link to={`/events/${e.id}`}><b>{e.title}</b></Link></td><td>{e.club_name}</td><td>{fmtDate(e.start)} {fmtRange(e.start, e.end)}</td><td><span className={`badge ${e.status === 'published' ? 'ok' : e.status === 'draft' ? 'mu' : 'gray'}`}>{e.status}</span></td><td>{e.registered}/{e.capacity}</td></tr>)}</tbody></table></div>)}
    {tab === 'conflicts' && (conflicts.loading ? <Spinner /> : conflicts.data.conflicts.length === 0 ? <Empty>No upcoming conflicts on campus.</Empty> : conflicts.data.conflicts.map((c) => (
      <div className="notice" key={c.event_id}><span className="badge">{c.affected_students} students</span><h3>{c.title}</h3><p>{c.venue} · {fmtDate(c.start)}</p><ul style={{ paddingLeft: 18 }}>{c.conflicts.map((x, i) => <li key={i}>{x.message}</li>)}</ul><Link className="btn" to={`/events/${c.event_id}`}>Open event</Link></div>)))}
  </>)
}
