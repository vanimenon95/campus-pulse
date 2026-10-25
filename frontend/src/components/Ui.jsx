import { useCallback, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Load data on mount: const { data, loading, error, reload } = useLoad(() => api.get('/x'), [deps]) */
export function useLoad(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then((data) => setState({ data, loading: false, error: null }))
      .catch((e) => setState({ data: null, loading: false, error: e.message }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(run, [run])
  return { ...state, reload: run }
}

export const Spinner = () => <div className="spinner" aria-label="Loading" />
export const Empty = ({ children }) => <div className="empty">{children}</div>
export const ErrorBox = ({ message, retry }) => (
  <div className="empty"><p className="err">{message}</p>{retry && <button className="btn sm" onClick={retry}>Try again</button>}</div>
)

export function Bar({ label, value, color }) {
  const p = Math.round((value || 0) * 100)
  return (
    <div className="bar">
      <div className="row"><span>{label}</span><b>{p}%</b></div>
      <div className="track"><div className="fill" style={{ width: `${p}%`, background: color }} /></div>
    </div>
  )
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <h2 style={{ marginBottom: 16 }}>{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map(([k, label]) => (
        <button key={k} role="tab" className={value === k ? 'on' : ''} onClick={() => onChange(k)}>{label}</button>
      ))}
    </div>
  )
}

export function Field({ label, children, hint }) {
  return <div className="field"><label>{label}</label>{children}{hint && <div className="hint">{hint}</div>}</div>
}

/** Redirects to /login when signed out, or home when the role is not allowed. */
export function Protected({ roles, children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}
