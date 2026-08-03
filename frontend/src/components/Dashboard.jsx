import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { Icon, initials } from '../icons.jsx'

const DIR_LABEL = { user_owes_them: 'I owe them', they_owe_user: 'They owe me', scheduling_loop: 'Scheduling', unanswered_question: 'Open question' }

export default function Dashboard({ ctx }) {
  const [threads, setThreads] = useState([])
  const [followups, setFollowups] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getThreads(), api.getFollowups()])
      .then(([t, f]) => { setThreads(t); setFollowups(f) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="wrap"><div className="loading">Loading dashboard…</div></div>

  const needs = threads.filter(t => t.needs_response_estimate)
  const risk = threads.filter(t => t.priority_label === 'risky_to_answer_fast')
  const emo = threads.filter(t => t.priority_label === 'emotional')
  const fu = followups.filter(f => f.status === 'open' || !f.status)

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="wrap">
      <div className="head">
        <div className="eyebrow">Overview</div>
        <h2>{greeting()}</h2>
        <p>{needs.length} conversations need a reply · {fu.length} open follow-ups · {risk.length} flagged to review</p>
      </div>

      {threads.length === 0 ? (
        <EmptyDashboard imessageOk={ctx.imessageOk} onSync={ctx.sync} syncing={ctx.syncing} onGo={ctx.go} />
      ) : (
        <>
          <div className="stat-row">
            <Tile icon="bell" label="Needs reply" n={needs.length} pop cap="people waiting on you" />
            <Tile icon="flag" label="Flagged" n={risk.length} cap="review before sending" />
            <Tile icon="followups" label="Follow-ups" n={fu.length} cap="open loops tracked" />
            <Tile icon="heart" label="Emotional" n={emo.length} cap="handle with care" />
          </div>

          <div className="dash-cols">
            <div className="panel">
              <div className="panel-h"><h3>Needs reply</h3><span className="more" onClick={() => ctx.go('inbox')}>Open inbox →</span></div>
              {needs.length ? needs.map(t => (
                <div key={t.id} className="lrow" onClick={() => ctx.openThread(t.id)}>
                  <div className="av">{initials(t.contact_name)}</div>
                  <div className="lr-body">
                    <div className="lr-top">
                      <span className="lr-name">{t.contact_name}</span>
                      <span className="lr-when">{fmtDate(t.latest_at)}</span>
                    </div>
                    <div className="lr-prev">{t.latest_message}</div>
                    <div className="lr-meta">
                      {t.priority_label === 'urgent' && <span className="tag solid">Urgent</span>}
                      {t.priority_label === 'risky_to_answer_fast' && <span className="tag flag">review</span>}
                      {t.priority_label === 'emotional' && <span className="tag pop">Emotional</span>}
                    </div>
                  </div>
                </div>
              )) : <div className="empty-row">All caught up 🎉</div>}
            </div>

            <div>
              <div className="panel">
                <div className="panel-h"><h3>Open follow-ups</h3><span className="more" onClick={() => ctx.go('followups')}>All →</span></div>
                {fu.length ? fu.slice(0, 4).map(f => (
                  <div key={f.id} className="lrow" onClick={() => ctx.go('followups')}>
                    <div className="lr-body">
                      <div className="lr-name" style={{ fontSize: 12.5 }}>{f.task_text}</div>
                      <div className="lr-meta">
                        <span className="dir">{DIR_LABEL[f.direction] || f.direction}</span>
                        {f.due_date && <span className="conf" style={{ fontStyle: 'normal', color: 'var(--pop)' }}>{f.due_date}</span>}
                      </div>
                    </div>
                  </div>
                )) : <div className="empty-row">No open items</div>}
              </div>

              <div className="panel">
                <div className="panel-h"><h3>iMessage sync</h3></div>
                <div style={{ padding: '16px 18px' }}>
                  <span className={`tag ${ctx.imessageOk ? 'good' : ''}`}>{ctx.imessageOk ? 'Read-only · local' : 'Not connected'}</span>
                  <p className="sm muted" style={{ marginTop: 10 }}>Connects to <b>chat.db</b> on your Mac. Never writes, never auto-sends.</p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Tile({ icon, label, n, pop, cap }) {
  return (
    <div className="tile">
      <div className="k"><Icon name={icon} /> {label}</div>
      <div className={`n${pop ? ' pop' : ''}`}>{n}</div>
      <div className="cap">{cap}</div>
    </div>
  )
}

function EmptyDashboard({ imessageOk, onSync, syncing, onGo }) {
  return (
    <div className="panel" style={{ padding: 32, textAlign: 'center' }}>
      <h3 style={{ fontSize: 16, marginBottom: 8 }}>No conversations yet</h3>
      <p className="muted sm" style={{ maxWidth: 420, margin: '0 auto 18px' }}>
        {imessageOk
          ? 'Click Sync Messages to pull your recent iMessage threads.'
          : 'iMessage isn’t accessible yet. On macOS, grant Full Disk Access to your terminal, then sync.'}
      </p>
      {imessageOk
        ? <button className="btn primary" onClick={onSync} disabled={syncing}>{syncing ? 'Syncing…' : 'Sync Messages'}</button>
        : <button className="btn" onClick={() => onGo('settings')}>Open Settings</button>}
    </div>
  )
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}
