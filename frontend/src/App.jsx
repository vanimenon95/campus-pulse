import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Protected } from './components/Ui'
import Home from './pages/Home'
import Events from './pages/Events'
import EventDetail from './pages/EventDetail'
import { Login, Register } from './pages/Auth'
import Clubs from './pages/Clubs'
import ClubDetail from './pages/ClubDetail'
import Venues from './pages/Venues'
import CalendarPage from './pages/CalendarPage'
import StudentDashboard from './pages/StudentDashboard'
import CoordinatorDashboard from './pages/CoordinatorDashboard'
import EventForm from './pages/EventForm'
import Attendance from './pages/Attendance'
import Reports from './pages/Reports'
import AdminDashboard from './pages/AdminDashboard'

const STAFF = ['coordinator', 'admin']
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="events" element={<Events />} />
        <Route path="events/:id" element={<EventDetail />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="clubs" element={<Clubs />} />
        <Route path="clubs/:id" element={<ClubDetail />} />
        <Route path="venues" element={<Venues />} />
        <Route path="calendar" element={<Protected><CalendarPage /></Protected>} />
        <Route path="dashboard" element={<Protected><StudentDashboard /></Protected>} />
        <Route path="coordinator" element={<Protected roles={STAFF}><CoordinatorDashboard /></Protected>} />
        <Route path="coordinator/events/new" element={<Protected roles={STAFF}><EventForm /></Protected>} />
        <Route path="coordinator/events/:id/edit" element={<Protected roles={STAFF}><EventForm /></Protected>} />
        <Route path="coordinator/events/:id/attendance" element={<Protected roles={STAFF}><Attendance /></Protected>} />
        <Route path="reports" element={<Protected roles={STAFF}><Reports /></Protected>} />
        <Route path="admin" element={<Protected roles={['admin']}><AdminDashboard /></Protected>} />
        <Route path="*" element={<div className="empty">Page not found.</div>} />
      </Route>
    </Routes>
  )
}
