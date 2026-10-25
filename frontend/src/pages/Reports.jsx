import { useState } from 'react'
import { api } from '../api/client'
import { ErrorBox, Spinner, Tabs, useLoad } from '../components/Ui'
import { fmtDate, pct } from '../utils/format'

export default function Reports() {
  const [tab, setTab] = useState('participation')
  const part = useLoad(() => api.get('/reports/participation'))
  const clubs = useLoad(() => api.get('/reports/clubs'))
  const venues = useLoad(() => api.get('/reports/venues'))
  const line = useLoad(() => api.get('/reports/timeline'))
  const csv = () => {
    const rows = [['Event', 'Club', 'Date', 'Registered', 'Capacity', 'Present', 'Recorded', 'Attendance rate'], ...part.data.events.map((e) => [e.title, e.club_name, e.start.slice(0, 10), e.registered, e.capacity, e.present, e.recorded, e.attendance_rate ?? ''])]
    const blob = new Blob([rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'participation-report.csv'; a.click()
  }
  const max = Math.max(1, ...(line.data?.weeks || []).map((w) => w.registrations))
  return (
    <>
      <div className="page-head"><div><h1>Reports & analytics</h1><p>Participation, club activity and venue utilization</p></div>{tab === 'participation' && part.data && <button className="btn" onClick={csv}>Download CSV</button>}</div>
      <Tabs value={tab} onChange={setTab} tabs={[['participation', 'Event participation'], ['clubs', 'Club activity'], ['venues', 'Venue utilization']]} />
      {tab === 'participation' && (part.loading ? <Spinner /> : part.error ? <ErrorBox message={part.error} retry={part.reload} /> : <>
        <div className="kpis"><div><b>{part.data.summary.events}</b><span>Events</span></div><div><b>{part.data.summary.registrations}</b><span>Registrations</span></div><div><b>{pct(part.data.summary.avg_attendance_rate)}</b><span>Avg attendance</span></div></div>
        {line.data && <div className="panel" style={{ marginBottom: 22, paddingBottom: 40 }}><h2>Registrations per week</h2><div className="tl">{line.data.weeks.map((w) => <div key={w.week} style={{ height: `${(w.registrations / max) * 100}%` }} title={`${w.registrations} registrations, ${w.events} events`}><span>{fmtDate(w.week)}</span></div>)}</div></div>}
        <div className="panel tablewrap"><table><thead><tr><th>Event</th><th>Date</th><th>Registered</th><th>Fill</th><th>Attendance</th></tr></thead><tbody>{part.data.events.map((e) => <tr key={e.event_id}><td><b>{e.title}</b><div className="hint">{e.club_name}</div></td><td>{fmtDate(e.start)}</td><td>{e.registered}/{e.capacity}</td><td>{pct(e.fill_rate)}</td><td>{e.attendance_rate != null ? `${pct(e.attendance_rate)} (${e.present}/${e.recorded})` : '—'}</td></tr>)}</tbody></table></div></>)}
      {tab === 'clubs' && (clubs.loading ? <Spinner /> : clubs.error ? <ErrorBox message={clubs.error} /> : <div className="panel tablewrap"><table><thead><tr><th>Club</th><th>Members</th><th>Events</th><th>Registrations</th><th>Attendance</th></tr></thead><tbody>{clubs.data.clubs.map((c) => <tr key={c.club_id}><td><b>{c.name}</b><div className="hint">{c.category}</div></td><td>{c.members}</td><td>{c.events}</td><td>{c.registrations}</td><td>{pct(c.attendance_rate)}</td></tr>)}</tbody></table></div>)}
      {tab === 'venues' && (venues.loading ? <Spinner /> : venues.error ? <ErrorBox message={venues.error} /> : <div className="panel">
        <p className="hint">Booked hours ÷ opening hours across the last and next 30 days (published events).</p>
        {venues.data.venues.map((v) => <div className="bar" key={v.venue_id}><div className="row"><span>{v.name} · {v.events} events · {v.booked_hours}h · avg fill {pct(v.avg_fill)}</span><b>{pct(v.utilization)}</b></div><div className="track"><div className="fill" style={{ width: `${v.utilization * 100}%`, background: 'var(--mustard)' }} /></div></div>)}</div>)}
    </>
  )
}
