import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { ErrorBox, Spinner, Modal, useLoad } from '../components/Ui'
import { fmtRange } from '../utils/format'

function Availability({ venue, onClose }) {
  const today = new Date().toISOString().slice(0, 10)
  const [date, setDate] = useState(today)
  const { data, loading, error } = useLoad(() => api.get(`/venues/${venue.id}/availability?date=${date}`), [venue.id, date])
  return (
    <Modal title={`${venue.name} — availability`} onClose={onClose}>
      <p className="hint">Open {venue.open_time}–{venue.close_time} · capacity {venue.capacity}</p>
      <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ maxWidth: 200, marginBottom: 14 }} />
      {loading ? <Spinner /> : error ? <p className="err">{error}</p> : (
        <>
          {data.bookings.length === 0 && data.blackouts.length === 0 && <p>✓ Free all day within opening hours.</p>}
          <ul className="ol">
            {data.bookings.map((b) => <li key={b.id}><span className="n">●</span><div><b>{b.title}</b><small>{fmtRange(b.start, b.end)} · {b.club_name} · {b.status}</small></div></li>)}
            {data.blackouts.map((b) => <li key={'b' + b.id}><span className="n" style={{ color: 'var(--red)', borderColor: 'var(--red)' }}>✕</span><div><b>Unavailable</b><small>{fmtRange(b.start, b.end)} · {b.reason}</small></div></li>)}
          </ul>
        </>)}
      <button className="btn sm" onClick={onClose} style={{ marginTop: 14 }}>Close</button>
    </Modal>
  )
}

export default function Venues() {
  const { user } = useAuth()
  const { data, loading, error, reload } = useLoad(() => api.get('/venues'))
  const [sel, setSel] = useState(null)
  return (
    <>
      <div className="page-head"><div><h1>Venues</h1><p>Capacities, facilities and live availability</p></div>
        {user?.role === 'admin' && <Link className="btn" to="/admin">Manage venues</Link>}</div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} retry={reload} /> :
        <div className="cards">{data.venues.map((v) => (
          <div className="card" key={v.id}>
            <h3>{v.name}</h3><div className="hint" style={{ color: '#555' }}>{v.location}</div>
            <div className="meta"><div><label>Capacity</label><b>{v.capacity}</b></div><div><label>Hours</label><b>{v.open_time}–{v.close_time}</b></div></div>
            <p>{v.facilities.join(' · ') || 'No listed facilities'}</p>
            <button className="btn dark" onClick={() => setSel(v)}>Check availability</button>
          </div>))}</div>}
      {sel && <Availability venue={sel} onClose={() => setSel(null)} />}
    </>
  )
}
