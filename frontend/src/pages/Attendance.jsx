import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useToast } from '../context/ToastContext'
import { ErrorBox, Spinner, useLoad } from '../components/Ui'
import { fmtLongDate, fmtRange, pct } from '../utils/format'

export default function Attendance() {
  const { id } = useParams(); const toast = useToast()
  const { data, loading, error, reload } = useLoad(() => api.get(`/events/${id}/registrations`), [id])
  const [marks, setMarks] = useState({}); const [busy, setBusy] = useState(false); const [q, setQ] = useState('')
  useEffect(() => { if (data) setMarks(Object.fromEntries(data.registrations.map((r) => [r.user_id, r.attended]))) }, [data])
  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} retry={reload} />
  const vals = Object.values(marks); const marked = vals.filter((v) => v !== null && v !== undefined); const present = marked.filter(Boolean).length
  const save = async () => {
    setBusy(true)
    try { const records = Object.entries(marks).filter(([, v]) => typeof v === 'boolean').map(([u, v]) => ({ user_id: +u, attended: v })); const r = await api.put(`/events/${id}/attendance`, { records }); toast.success(r.message); reload() }
    catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  const all = (v) => setMarks(Object.fromEntries(data.registrations.map((r) => [r.user_id, v])))
  const list = data.registrations.filter((r) => r.name.toLowerCase().includes(q.toLowerCase()))
  const e = data.event
  return (
    <>
      <div className="page-head"><div><h1>Attendance</h1><p>{e.title} · {fmtLongDate(e.start)}, {fmtRange(e.start, e.end)}</p></div><Link className="btn" to="/coordinator">← Back</Link></div>
      <div className="kpis"><div><b>{data.summary.registered}</b><span>Registered</span></div><div><b>{present}</b><span>Present (unsaved incl.)</span></div><div><b>{marked.length ? pct(present / marked.length) : '–'}</b><span>Attendance rate</span></div><div><b>{pct(data.summary.registered ? marked.length / data.summary.registered : 0)}</b><span>Marked</span></div></div>
      <div className="toolbar"><input className="input" placeholder="Search students…" value={q} onChange={(x) => setQ(x.target.value)} />
        <button className="btn sm" onClick={() => all(true)}>Mark all present</button><button className="btn sm" onClick={() => all(false)}>Mark all absent</button><button className="btn primary" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save attendance'}</button></div>
      <div className="panel tablewrap"><table><thead><tr><th>Student</th><th>Registered</th><th>Status</th></tr></thead><tbody>
        {list.map((r) => <tr key={r.user_id}><td><b>{r.name}</b><div className="hint">{r.email}</div></td><td>{new Date(r.registered_at).toLocaleDateString()}</td>
          <td><div className="actions"><button className={`chip ${marks[r.user_id] === true ? 'on' : ''}`} onClick={() => setMarks({ ...marks, [r.user_id]: true })}>Present</button><button className={`chip ${marks[r.user_id] === false ? 'on' : ''}`} onClick={() => setMarks({ ...marks, [r.user_id]: false })}>Absent</button></div></td></tr>)}</tbody></table></div>
    </>
  )
}
