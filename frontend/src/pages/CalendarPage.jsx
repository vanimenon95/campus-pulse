import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { ErrorBox, Spinner, useLoad } from '../components/Ui'
import { fmtTime } from '../utils/format'

export default function CalendarPage() {
  const [cursor, setCursor] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const { data, loading, error, reload } = useLoad(() => api.get('/me/dashboard'))
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} retry={reload} />
  const events = [...data.upcoming, ...data.past]
  const clashIds = new Set(data.my_clashes.flatMap((c) => [c.a_id, c.b_id]))
  const first = new Date(cursor); const offset = (first.getDay() + 6) % 7
  const days = Array.from({ length: 42 }, (_, i) => new Date(first.getFullYear(), first.getMonth(), 1 - offset + i))
  const same = (a, b) => a.toDateString() === b.toDateString()
  return (
    <>
      <div className="page-head"><div><h1>{cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h1><p>Your registered events. Red edge = clashes with another of your events.</p></div>
        <div className="actions"><button className="btn sm" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>← Prev</button>
          <button className="btn sm" onClick={() => { const d = new Date(); setCursor(new Date(d.getFullYear(), d.getMonth(), 1)) }}>Today</button>
          <button className="btn sm" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>Next →</button></div></div>
      <div className="tablewrap"><div className="cal" style={{ minWidth: 640 }}>
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div className="dow" key={d}>{d}</div>)}
        {days.map((d) => (
          <div key={d.toISOString()} className={`day ${d.getMonth() !== cursor.getMonth() ? 'dim' : ''} ${same(d, new Date()) ? 'today' : ''}`}>
            {d.getDate()}
            {events.filter((e) => same(new Date(e.start), d)).map((e) => (
              <Link key={e.id} to={`/events/${e.id}`} className={`ev ${clashIds.has(e.id) ? 'bad' : ''}`}>{fmtTime(e.start)} {e.title}</Link>))}
          </div>))}
      </div></div>
    </>
  )
}
