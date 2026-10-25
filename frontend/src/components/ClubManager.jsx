import { useState } from 'react'
import { api } from '../api/client'
import { useToast } from '../context/ToastContext'
import { Field, Modal, Spinner, useLoad } from './Ui'
import { fmtDate } from '../utils/format'

const CATS = ['Tech', 'Culture', 'Sports', 'Academic', 'Social']

export function CreateClubForm({ onDone }) {
  const toast = useToast()
  const [f, setF] = useState({ name: '', category: 'Tech', description: '' }); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    if (f.name.trim().length < 3) return setErr('Club name must be at least 3 characters.')
    setBusy(true)
    try { await api.post('/clubs', f); toast.success('Club created.'); setF({ name: '', category: 'Tech', description: '' }); onDone() }
    catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }
  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="f2"><Field label="Club name"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Category"><select className="select" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{CATS.map((c) => <option key={c}>{c}</option>)}</select></Field></div>
      <Field label="Description"><textarea className="textarea" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
      {err && <div className="err">{err}</div>}<button className="btn primary" disabled={busy}>{busy ? 'Creating…' : 'Create club'}</button>
    </form>
  )
}

function ManageModal({ club, onClose, onChanged }) {
  const toast = useToast()
  const members = useLoad(() => api.get(`/clubs/${club.id}/members`), [club.id])
  const detail = useLoad(() => api.get(`/clubs/${club.id}`), [club.id])
  const [email, setEmail] = useState(''); const [post, setPost] = useState({ title: '', body: '' })
  const run = async (fn, ok, after) => { try { await fn(); toast.success(ok); after?.(); onChanged() } catch (e) { toast.error(e.message) } }
  return (
    <Modal title={`Manage ${club.name}`} onClose={onClose}>
      <span className="lbl">Add member by email</span>
      <div className="actions" style={{ margin: '6px 0 16px' }}><input className="input" style={{ flex: 1 }} placeholder="student@campus.test" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button className="btn sm primary" onClick={() => run(() => api.post(`/clubs/${club.id}/members`, { email }), 'Member added.', () => { setEmail(''); members.reload() })}>Add</button></div>
      <span className="lbl">Members ({members.data?.members.length ?? '…'})</span>
      {members.loading ? <Spinner /> : <div style={{ maxHeight: 180, overflow: 'auto' }}><table><tbody>{members.data.members.slice(0, 100).map((m) => (
        <tr key={m.user_id}><td>{m.name}<div className="hint">{m.email}</div></td><td><button className="btn sm danger" onClick={() => run(() => api.del(`/clubs/${club.id}/members/${m.user_id}`), 'Member removed.', members.reload)}>Remove</button></td></tr>))}</tbody></table></div>}
      <h3 style={{ margin: '22px 0 10px', fontSize: 17 }}>Publish a club activity</h3>
      <div className="form wide"><input className="input" placeholder="Title" value={post.title} onChange={(e) => setPost({ ...post, title: e.target.value })} />
        <textarea className="textarea" placeholder="Details for members…" value={post.body} onChange={(e) => setPost({ ...post, body: e.target.value })} />
        <button className="btn sm primary" onClick={() => run(() => api.post(`/clubs/${club.id}/activities`, post), 'Published to all members.', () => { setPost({ title: '', body: '' }); detail.reload() })}>Publish</button></div>
      {(detail.data?.club.activities || []).slice(0, 4).map((a) => (
        <div key={a.id} style={{ borderTop: '1px solid var(--line)', padding: '8px 0', display: 'flex', justifyContent: 'space-between', gap: 10 }}><div><b>{a.title}</b><div className="hint">{fmtDate(a.created_at)}</div></div>
          <button className="btn sm" onClick={() => run(() => api.del(`/clubs/${club.id}/activities/${a.id}`), 'Removed.', detail.reload)}>Delete</button></div>))}
      <button className="btn sm" style={{ marginTop: 16 }} onClick={onClose}>Close</button>
    </Modal>
  )
}

/** Table of clubs with Manage buttons + create-club form. `clubs` comes from the dashboard API. */
export default function ClubManager({ clubs, reload }) {
  const [sel, setSel] = useState(null)
  return (
    <div className="grid2">
      <div className="panel"><h2>Your clubs</h2>
        {clubs.length === 0 ? <p className="hint">No clubs yet. Create one →</p> : <div className="tablewrap"><table><thead><tr><th>Club</th><th>Category</th><th>Members</th><th /></tr></thead><tbody>
          {clubs.map((c) => <tr key={c.id}><td><b>{c.name}</b></td><td>{c.category}</td><td>{c.member_count}</td><td><button className="btn sm" onClick={() => setSel(c)}>Manage</button></td></tr>)}</tbody></table></div>}</div>
      <div className="panel"><h2>Create a club</h2><CreateClubForm onDone={reload} /></div>
      {sel && <ManageModal club={sel} onClose={() => setSel(null)} onChanged={reload} />}
    </div>
  )
}
