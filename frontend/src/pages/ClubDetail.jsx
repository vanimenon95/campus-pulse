import { useParams, Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, useLoad } from '../components/Ui'
import Ticket from '../components/Ticket'
import { fmtDate } from '../utils/format'

export default function ClubDetail() {
  const { id } = useParams(); const { user } = useAuth(); const toast = useToast(); const nav = useNavigate()
  const club = useLoad(() => api.get(`/clubs/${id}`), [id, user?.id])
  const events = useLoad(() => api.get(`/events?upcoming=1&club_id=${id}`), [id, user?.id])
  if (club.loading) return <Spinner />
  if (club.error) return <ErrorBox message={club.error} retry={club.reload} />
  const c = club.data.club
  const toggle = async () => {
    if (!user) return nav('/login', { state: { from: `/clubs/${id}` } })
    try { c.joined ? await api.del(`/clubs/${id}/join`) : await api.post(`/clubs/${id}/join`); toast.success(c.joined ? 'You left the club.' : 'Welcome to the club!'); club.reload() }
    catch (e) { toast.error(e.message) }
  }
  return (
    <>
      <div className="page-head"><div><h1>{c.name}</h1><p>{c.description} · {c.member_count} members · {c.coordinator_name}</p></div>
        <div className="actions"><button className={`btn ${c.joined ? '' : 'primary'}`} onClick={toggle}>{c.joined ? '✓ Joined — leave' : 'Join club'}</button>
          {c.can_manage && <Link className="btn" to="/coordinator">Manage club</Link>}</div></div>
      <div className="grid2">
        <div><h2 style={{ marginBottom: 16 }}>Upcoming events</h2>
          {events.loading ? <Spinner /> : (events.data?.events || []).length === 0 ? <Empty>No upcoming events.</Empty> :
            <div style={{ display: 'grid', gap: 22 }}>{events.data.events.map((e) => <Ticket key={e.id} event={e} mini />)}</div>}</div>
        <div className="panel"><h2>Club activity</h2>
          {c.activities.length === 0 ? <p className="hint">Nothing published yet.</p> : c.activities.map((a) => (
            <div key={a.id} style={{ borderTop: '1px solid var(--line)', padding: '12px 0' }}><b>{a.title}</b><div className="hint">{fmtDate(a.created_at)}</div><div>{a.body}</div></div>))}</div>
      </div>
    </>
  )
}
