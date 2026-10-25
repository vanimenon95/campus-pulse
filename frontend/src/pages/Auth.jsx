import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { homeFor, useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Field } from '../components/Ui'

const DEMO = [['Student', 'student@campus.test', 'Student@123'], ['Coordinator', 'rahul@campus.test', 'Coord@123'], ['Admin', 'admin@campus.test', 'Admin@123']]

export function Login() {
  const { login } = useAuth(); const toast = useToast(); const nav = useNavigate(); const loc = useLocation()
  const [f, setF] = useState({ email: '', password: '' }); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    if (!f.email || !f.password) return setErr('Enter your email and password.')
    setBusy(true)
    try { const u = await login(f.email, f.password); toast.success(`Welcome back, ${u.name.split(' ')[0]}!`); nav(loc.state?.from || homeFor(u)) }
    catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }
  return (
    <div className="auth panel">
      <h1>Sign in</h1><p className="hint">Welcome back to Campus Pulse.</p>
      <form className="form" onSubmit={submit} noValidate>
        <Field label="Email"><input className="input" type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Password"><input className="input" type="password" autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        {err && <div className="err" role="alert">{err}</div>}
        <button className="btn primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="hint">New here? <Link to="/register" style={{ color: 'var(--mustard)' }}>Create an account</Link></p>
      <div className="rec"><span className="lbl">Demo accounts (click to fill)</span>
        <div className="actions" style={{ marginTop: 8 }}>{DEMO.map(([n, e, p]) => <button key={n} type="button" className="btn sm" onClick={() => setF({ email: e, password: p })}>{n}</button>)}</div>
      </div>
    </div>
  )
}

export function Register() {
  const { register } = useAuth(); const toast = useToast(); const nav = useNavigate()
  const [f, setF] = useState({ name: '', email: '', password: '', department: '' }); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    if (f.name.trim().length < 2) return setErr('Please enter your full name.')
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email)) return setErr('Please enter a valid email.')
    if (f.password.length < 8) return setErr('Password must be at least 8 characters.')
    setBusy(true)
    try { await register(f); toast.success('Account created. Welcome to Campus Pulse!'); nav('/dashboard') }
    catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }
  return (
    <div className="auth panel">
      <h1>Create account</h1><p className="hint">Students sign up here. Coordinator access is granted by an admin.</p>
      <form className="form" onSubmit={submit} noValidate>
        <Field label="Full name"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Email"><input className="input" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Department (optional)"><input className="input" value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} /></Field>
        <Field label="Password" hint="At least 8 characters"><input className="input" type="password" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        {err && <div className="err" role="alert">{err}</div>}
        <button className="btn primary" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
      </form>
      <p className="hint">Already have an account? <Link to="/login" style={{ color: 'var(--mustard)' }}>Sign in</Link></p>
    </div>
  )
}
