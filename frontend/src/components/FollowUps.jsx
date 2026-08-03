import { useState, useEffect } from 'react'
import { api } from '../api.js'

const DIR_LABEL = { user_owes_them: 'I owe them', they_owe_user: 'They owe me', scheduling_loop: 'Scheduling', unanswered_question: 'Open question' }
const FILTERS = [['all', 'All'], ['user_owes_them', 'I owe them'], ['they_owe_user', 'They owe me'], ['scheduling_loop', 'Scheduling'], ['unanswered_question', 'Open question']]

export default function FollowUps({ ctx }) {
  const [items, setItems] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])
  async function load() {
    try { setItems(await api.getFollowups()) }
    catch (e) { ctx.toast(e.message, 'error') }
    finally { setLoading(false) }
  }
  async function complete(id) {
    await api.completeFollowup(id)
    setItems(i => i.filter(x => x.id !== id))
    ctx.toast('Marked complete')
  }

  const filtered = filter === 'all' ? items : items.filter(f => f.direction === filter)
  const groups = {}
  filtered.forEach(f => { (groups[f.direction] = groups[f.direction] || []).push(f) })

  return (
    <div className="wrap">
      <div className="head"><div className="eyebrow">Tasks</div><h2>Follow-ups</h2><p>{items.length} open items pulled from your conversations</p></div>

      <div className="filters" style={{ marginBottom: 8 }}>
        {FILTERS.map(([id, label]) => (
          <button key={id} className={`chip ${filter === id ? 'on' : ''}`} onClick={() => setFilter(id)}>{label}</button>
        ))}
      </div>

      {loading && <div className="loading">Loading follow-ups…</div>}
      {!loading && filtered.length === 0 && <div className="empty">No open follow-ups 🎉</div>}

      {Object.entries(groups).map(([dir, list]) => (
        <div key={dir}>
          <div className="sec-title" style={{ marginTop: 24 }}>{DIR_LABEL[dir] || dir}</div>
          <div className="panel">
            {list.map(f => (
              <div key={f.id} className="fu">
                <div>
                  <div className="task">{f.task_text}</div>
                  <div className="fu-meta">
                    <span className="dir">{DIR_LABEL[f.direction] || f.direction}</span>
                    {f.contact_name && <span className="sm muted">{f.contact_name}</span>}
                    {f.due_date && <span className="sm" style={{ color: 'var(--pop)' }}>Due: {f.due_date}</span>}
                    <span className="conf">{f.confidence} conf</span>
                  </div>
                </div>
                <button className="btn" onClick={() => complete(f.id)}>Done</button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
