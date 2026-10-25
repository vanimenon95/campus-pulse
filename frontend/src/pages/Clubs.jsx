import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, useLoad } from '../components/Ui'
import { catColor } from '../utils/format'

export default function Clubs() {
  const { user } = useAuth(); const toast = useToast(); const nav = useNavigate()
  const [q, setQ] = useState(''); const [mine, setMine] = useState(false)
  const { data, loading, error, reload } = useLoad(() => api.get('/clubs?q=' + encodeURIComponent(q)), [q, user?.id])
  const toggle = async (c) => {
    if (!user) return nav('/login', { state: { from: '/clubs' } })
    try { c.joined ? await api.del(`/clubs/${c.id}/join`) : await api.post(`/clubs/${c.id}/join`); toast.success(c.joined ? `You left ${c.name}.` : `You joined ${c.name}.`); reload() }
    catch (e) { toast.error(e.message) }
  }
  const clubs = (data?.clubs || []).filter((c) => !mine || c.joined)
  return (
    <>
      <div className="page-head"><div><h1>Clubs</h1><p>Find your people.</p></div>
        {user && <div className="chips"><button className={`chip ${!mine ? 'on' : ''}`} onClick={() => setMine(false)}>All clubs</button><button className={`chip ${mine ? 'on' : ''}`} onClick={() => setMine(true)}>My clubs</button></div>}</div>
      <div className="toolbar"><input className="input" placeholder="Search clubs…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search clubs" /></div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} retry={reload} /> : clubs.length === 0 ? <Empty>{mine ? "You haven't joined any clubs yet." : 'No clubs found.'}</Empty> :
        <div className="cards">{clubs.map((c) => (
          <div className="card" key={c.id}>
            <span className="tag" style={{ background: catColor(c.category), alignSelf: 'flex-start' }}>{c.category}</span>
            <h3><Link to={`/clubs/${c.id}`}>{c.name}</Link></h3><p>{c.description}</p>
            <div className="hint" style={{ color: '#555' }}>{c.member_count} members · led by {c.coordinator_name || '—'}</div>
            <button className={`btn ${c.joined ? 'dark' : ''}`} style={c.joined ? {} : { borderColor: 'var(--ink)', color: 'var(--ink)' }} onClick={() => toggle(c)}>{c.joined ? '✓ Joined' : 'Join club'}</button>
          </div>))}</div>}
    </>
  )
}
