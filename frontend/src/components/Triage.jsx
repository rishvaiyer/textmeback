import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import { Icon } from '../icons.jsx'
import { Pulse, openLabel } from './Pulse.jsx'

// Clear the replies you owe, one conversation at a time.
// Copying a reply or snoozing hides the thread until tomorrow (kept on this device); "no reply needed" tells the server.
const RANK = { urgent: 0, risky_to_answer_fast: 1, emotional: 2 }
const HIGH_RISK = ['medical', 'money', 'legal', 'conflict', 'work_risk']
const QUICK = [['shorter', 'shorter'], ['nicer', 'nicer'], ['more_direct', 'more direct'], ['calmer', 'calmer'], ['say_no_politely', 'say no politely'], ['buy_time', 'buy time']]
const KEY = 'tmb-triage-hidden'

const dayStamp = (offset = 0) => { const d = new Date(); d.setDate(d.getDate() + offset); return d.toISOString().slice(0, 10) }
function hiddenNow() {
  try { const m = JSON.parse(localStorage.getItem(KEY) || '{}'); const today = dayStamp(); return new Set(Object.keys(m).filter(id => m[id] > today).map(Number)) } catch { return new Set() }
}
function hideUntilTomorrow(id) {
  try { const m = JSON.parse(localStorage.getItem(KEY) || '{}'); m[id] = dayStamp(1); localStorage.setItem(KEY, JSON.stringify(m)) } catch { /* private mode */ }
}
const fmt = iso => iso ? new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : ''

export default function Triage({ ctx }) {
  const [queue, setQueue] = useState(null)
  const [total, setTotal] = useState(0)
  const [log, setLog] = useState([])
  const [thread, setThread] = useState(null)
  const [draft, setDraft] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getThreads().then(all => {
      const hidden = hiddenNow()
      const q = all.filter(t => t.needs_response_estimate && !hidden.has(t.id))
        .sort((a, b) => (RANK[a.priority_label] ?? 3) - (RANK[b.priority_label] ?? 3) || new Date(a.latest_at) - new Date(b.latest_at))
        .map(t => t.id)
      setQueue(q); setTotal(q.length)
    }).catch(() => setQueue([]))
  }, [])

  const current = queue && queue[0]
  useEffect(() => {
    if (!current) { setThread(null); return }
    let alive = true
    setThread(null); setDraft(null); setText('')
    api.getThread(current).then(async t => {
      if (!alive) return
      setThread(t)
      const existing = t.drafts?.[0]
      if (existing) { setDraft(existing); setText(existing.draft_text); return }
      try { const r = await api.generateDraft(current); if (alive) { setDraft(r); setText(r.draft_text) } } catch (e) { ctx.toast(e.message, 'error') }
    }).catch(e => ctx.toast(e.message, 'error'))
    return () => { alive = false }
  }, [current])

  const finish = useCallback((kind, label) => {
    setLog(l => [...l, { id: current, name: thread?.contact_name || 'Conversation', label }])
    setQueue(q => q.slice(1))
  }, [current, thread])

  const act = useCallback(async kind => {
    if (!current || !queue?.length) return
    if (kind === 'skip') { if (queue.length > 1) setQueue(q => [...q.slice(1), q[0]]); return }
    try {
      if (kind === 'copy') {
        try { await navigator.clipboard.writeText(text) } catch { /* the server copy below is the fallback */ }
        await api.copyDraft(current)
        hideUntilTomorrow(current)
        ctx.toast('Copied. Paste it wherever you like. TextMeBack never sends.')
        finish(kind, 'Reply copied')
      } else if (kind === 'snooze') {
        hideUntilTomorrow(current); ctx.toast('Snoozed to tomorrow'); finish(kind, 'Snoozed to tomorrow')
      } else if (kind === 'none') {
        await api.noResponse(current); ctx.toast('Marked as no reply needed'); finish(kind, 'No reply needed')
      }
    } catch (e) { ctx.toast(e.message, 'error') }
  }, [current, queue, text, finish, ctx])

  async function rewrite(type) {
    if (!text) return
    setBusy(true)
    try { const r = await api.rewriteDraft(current, text, type); setText(r.draft_text) } catch (e) { ctx.toast(e.message, 'error') } finally { setBusy(false) }
  }

  useEffect(() => {
    const onKey = e => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName)
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); act('copy'); return }
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return
      const k = e.key.toLowerCase()
      if (k === 's') act('skip'); else if (k === 'z') act('snooze'); else if (k === 'n') act('none')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [act])

  if (queue === null) return <div className="wrap"><div className="loading">Loading your replies…</div></div>

  if (!queue.length) {
    const n = k => log.filter(x => x.label === k).length
    const parts = [n('Reply copied') && `${n('Reply copied')} replies copied`, n('Snoozed to tomorrow') && `${n('Snoozed to tomorrow')} snoozed`, n('No reply needed') && `${n('No reply needed')} needed no reply`].filter(Boolean)
    return (
      <div className="wrap tri-done">
        <div className="eyebrow">Triage</div>
        <h2>{log.length ? 'That is everyone.' : 'Nothing to answer.'}</h2>
        <p className="sum">{parts.length ? `${parts.join(', ')}. Nothing was sent: you paste each reply yourself.` : 'Every conversation is answered or snoozed. Sync to check for new messages.'}</p>
        {log.length > 0 && <ul className="tri-log">{log.map(x => <li key={x.id}><b>{x.name}</b><span className="what">{x.label}</span></li>)}</ul>}
        <div className="head-actions"><button className="btn primary big" onClick={() => ctx.go('dashboard')}>Back to home</button></div>
      </div>
    )
  }

  const riskFlags = draft ? (draft.risk_flags || (draft.risk_flags_json ? JSON.parse(draft.risk_flags_json) : [])) : []
  const sensitive = riskFlags.some(f => HIGH_RISK.includes(f))
  const initials = (thread?.contact_name || '?').replace(/\(.*\)/, '').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
  const mac = /Mac/.test(navigator.platform)

  return (
    <div className="wrap triage">
      <div className="tri-bar">
        <div className="tri-prog" role="progressbar" aria-label="Triage progress" aria-valuenow={log.length} aria-valuemin="0" aria-valuemax={total}>
          {Array.from({ length: total }, (_, i) => <i key={i} className={i < log.length ? 'done' : i === log.length ? 'now' : ''} />)}
        </div>
        <span className="tri-count"><b>{log.length + 1}</b> of {total}</span>
        <button className="btn ghost" onClick={() => ctx.go('dashboard')}>Exit</button>
      </div>

      {!thread ? <div className="loading">Opening the conversation…</div> : (
        <div className="tri-grid">
          <section className="tri-card" aria-label="Conversation">
            <div className="tri-who">
              <span className="av">{initials}</span>
              <div><h2>{thread.contact_name}</h2><p>{(thread.priority_label || 'needs reply').replace(/_/g, ' ')}.</p></div>
            </div>
            {riskFlags.length > 0 && <div className="a-meta">{riskFlags.map(f => <span key={f} className="tag flag">{f.replace('_', ' ')}</span>)}</div>}
            <div className="convo">
              {(thread.messages || []).slice(-3).map(m => (
                <div key={m.id} className={`msg ${m.is_from_me ? 'me' : 'them'}`}>
                  <div className="bubble">{m.text}</div><div className="time">{fmt(m.created_at)}</div>
                </div>
              ))}
            </div>
            {thread.messages?.length > 0 && (
              <div className="d-pulse">
                <div className="ph"><b>Last 14 days</b><span className="num">{openLabel(thread.messages)}</span></div>
                <Pulse messages={thread.messages} />
              </div>
            )}
          </section>

          <section className="tri-card" aria-label="Reply">
            <div className="composer">
              <span className="rw-label" style={{ marginTop: 0 }}>Suggested reply</span>
              <div className="reason">{draft?.reason || 'Writing a suggestion…'}</div>
              <div className="draft-card">
                <textarea aria-label="Draft reply" value={text} onChange={e => setText(e.target.value)} />
                <div className="draft-foot"><span>{text.trim() ? text.trim().split(/\s+/).length : 0} words</span><span>{mac ? '⌘' : 'Ctrl'}↵ copies and moves on</span></div>
              </div>
              {sensitive && (
                <div className="notice"><Icon name="alert" /><div><b>Read this one before you copy it.</b> The thread touches {riskFlags.join(', ').replace(/_/g, ' ')}. TextMeBack copies to your clipboard and stops there.</div></div>
              )}
              <span className="rw-label">Rewrite</span>
              <div className="rewrites">
                {QUICK.map(([id, label]) => <button key={id} className="rw" disabled={busy} onClick={() => rewrite(id)}>{label}</button>)}
              </div>
            </div>
          </section>
        </div>
      )}

      <div className="tri-actions">
        <span className="grow">{queue.length > 1 ? `${queue.length - 1} more after this` : 'Last one'}</span>
        <button className="btn ghost" onClick={() => act('skip')} disabled={queue.length < 2}>Skip <kbd>S</kbd></button>
        <button className="btn" onClick={() => act('snooze')} title="Hide until tomorrow">Snooze <kbd>Z</kbd></button>
        <button className="btn" onClick={() => act('none')}>No reply needed <kbd>N</kbd></button>
        <button className="btn primary big" onClick={() => act('copy')} disabled={!text}><Icon name="copy" /> Copy and next <kbd>{mac ? '⌘' : 'Ctrl'}↵</kbd></button>
      </div>
    </div>
  )
}
