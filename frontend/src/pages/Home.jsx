import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useLoad, Spinner } from '../components/Ui'
import Ticket from '../components/Ticket'
import { useAuth } from '../context/AuthContext'

export default function Home() {
  const { user } = useAuth()
  const stats = useLoad(() => api.get('/stats'))
  const feed = useLoad(() => api.get('/events?upcoming=1'))
  const events = feed.data?.events || []
  // featured: the three best-attended upcoming events
  const featured = [...events].sort((a, b) => b.registered - a.registered).slice(0, 3)
  const s = stats.data
  return (
    <section className="hero">
      <div>
        <span className="eyebrow">AI keeps your week conflict-free</span>
        <h1>One home for every club, every stage, every event.</h1>
        <p className="lead">Clubs post it, students claim a seat, and the schedule sorts itself out — no more two great events fighting for the same hour.</p>
        <div className="cta">
          <Link to="/events" className="btn primary">Explore this week</Link>
          <Link to={user ? '/clubs' : '/register'} className="btn">{user ? 'Browse clubs' : 'Register your club'}</Link>
        </div>
        <div className="stats">
          <div><b>{s ? s.active_clubs : '–'}</b><span>Active clubs</span></div>
          <div><b>{s ? s.events_this_term : '–'}</b><span>Events this term</span></div>
          <div><b>{s ? `${s.conflict_free_pct}%` : '–'}</b><span>Conflict-free</span></div>
        </div>
      </div>
      <div className="hero-tickets">
        {feed.loading ? <Spinner /> : featured.map((e) => <Ticket key={e.id} event={e} mini compact />)}
      </div>
    </section>
  )
}
