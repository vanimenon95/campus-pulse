import { Link } from 'react-router-dom'
import { catColor, fmtDate, fmtRange } from '../utils/format'

/** Ticket-style event card (see PPT slides 10-11). */
export default function Ticket({ event: e, onJoin, busy, mini, compact }) {
  const color = catColor(e.category)
  const flags = e.flags
  const full = e.registered >= e.capacity
  return (
    <article className={`ticket ${mini ? 'mini' : ''} ${compact ? 'compact' : ''}`}>
      <span className="notch t" style={{ background: color }} /><span className="notch b" style={{ background: color }} />
      <div className="main">
        <span className="tag" style={{ background: color }}>{e.club_name}</span>
        <h3><Link to={`/events/${e.id}`}>{e.title}</Link></h3>
        <div className="meta">
          {!compact && <div><label>Date</label><b>{fmtDate(e.start)}</b></div>}
          {!compact && <div><label>Time</label><b>{fmtRange(e.start, e.end)}</b></div>}
          <div><label>Venue</label><b>{e.venue_name}</b></div>
        </div>
        {flags?.venue_conflict && <span className="conflict-stamp">Venue conflict</span>}
        {!flags?.venue_conflict && flags?.affected_students > 0 && (
          <span className="conflict-stamp">Schedule conflict — {flags.affected_students} students</span>
        )}
      </div>
      <div className="stub">
        <div className="going">{e.registered}<small>GOING</small></div>
        {!mini && (
          e.user_registered
            ? <Link className="btn dark sm" to={`/events/${e.id}`} style={{ textAlign: 'center' }}>✓ Registered</Link>
            : <button className="btn dark" disabled={busy || full} onClick={() => onJoin?.(e)}>{full ? 'Full' : 'Join event'}</button>
        )}
      </div>
    </article>
  )
}
