import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { homeFor, useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { initials } from '../utils/format'

export default function Layout() {
  const { user, logout } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  const [menu, setMenu] = useState(false)
  useEffect(() => { setOpen(false); setMenu(false); window.scrollTo(0, 0) }, [loc.pathname])

  const signOut = async () => { await logout(); toast.success('Signed out.'); nav('/') }
  const link = ({ isActive }) => (isActive ? 'active' : '')
  return (
    <>
      <header className="site-header">
        <div className="wrap">
          <Link to="/" className="logo">CAMPUS<i>·</i>PULSE</Link>
          <nav className={`nav ${open ? 'open' : ''}`} aria-label="Main">
            <NavLink to="/events" className={link}>Discover</NavLink>
            <NavLink to="/clubs" className={link}>My clubs</NavLink>
            <NavLink to="/calendar" className={link}>Calendar</NavLink>
            <NavLink to="/venues" className={link}>Venues</NavLink>
          </nav>
          <div className="hdr-right">
            {user ? (
              <div className="rel">
                <button className="avatar" onClick={() => setMenu(!menu)} aria-label="Account menu">{initials(user.name)}</button>
                {menu && (
                  <div className="menu">
                    <div className="who">{user.name}<br />{user.role}</div>
                    <Link to={homeFor(user)}>Dashboard</Link>
                    {user.role !== 'student' && <Link to="/coordinator/events/new">Create event</Link>}
                    {user.role !== 'student' && <Link to="/reports">Reports</Link>}
                    <button onClick={signOut}>Sign out</button>
                  </div>
                )}
              </div>
            ) : (
              <Link to="/login" className="btn sm" style={{ padding: '10px 18px' }}>Sign in</Link>
            )}
            <button className="burger" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
          </div>
        </div>
      </header>
      <main><div className="wrap"><Outlet /></div></main>
      <footer className="footer"><div className="wrap"><span>CAMPUS·PULSE — AI-Powered College Club & Event Coordination</span><span>Fictional demo data</span></div></footer>
    </>
  )
}
