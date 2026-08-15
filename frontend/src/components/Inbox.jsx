import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { Icon } from '../icons.jsx'
import { Pulse, PulseLegend, openLabel } from './Pulse.jsx'

const REWRITES = [
  ['shorter', 'shorter'], ['nicer', 'nicer'], ['more_direct', 'more direct'], ['less_fake', 'less fake'],
  ['more_adult', 'more adult'], ['casual', 'casual'], ['professional', 'professional'], ['say_no_politely', 'say no politely'],
  ['buy_time', 'buy time'], ['ask_one_clear_question', 'one clear question'], ['calmer', 'calmer'],
  ['less_defensive', 'less defensive'], ['less_apologetic', 'less apologetic'],
]
const HIGH_RISK = ['medical', 'money', 'legal', 'conflict', 'work_risk']

export default function Inbox({ ctx, initialThread }) {
  const [threads, setThreads] = useState([])
  const [filter, setFilter] = useState('needs')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(initialThread || null)
  const [thread, setThread] = useState(null)
  const [draft, setDraft] = useState(null)
  const [draftText, setDraftText] = useState('')
  const [toneRisks, setToneRisks] = useState(null)
  const [pane, setPane] = useState(initialThread ? 'detail' : 'list')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getThreads().then(t => {
      setThreads(t)
      setLoading(false)
      if (initialThread) loadThread(initialThread)
    }).catch(() => setLoading(false))
  }, [])

  async function loadThread(id) {
    setSelected(id); setPane('detail'); setDraft(null); setDraftText(''); setToneRisks(null)
    const t = await api.getThread(id)
    setThread(t)
    if (t.drafts?.length) {
      setDraft(t.drafts[0])
      setDraftText(t.drafts[0].draft_text)
    }
  }

  async function generate() {
    setBusy(true)
    try {
      const r = await api.generateDraft(selected)
      setDraft(r); setDraftText(r.draft_text); setToneRisks(r.tone_risks)
    } catch (e) { ctx.toast(e.message, 'error') } finally { setBusy(false) }
  }

  async function rewrite(type) {
    if (!draftText) return
    setBusy(true)
    try {
      const r = await api.rewriteDraft(selected, draftText, type)
      setDraftText(r.draft_text); setToneRisks(r.tone_risks)
    } catch (e) { ctx.toast(e.message, 'error') } finally { setBusy(false) }
  }

  async function decide(kind) {
    try {
      if (kind === 'approve') { await api.approve(selected, 'approved', draftText); ctx.toast('Approved & saved') }
      else if (kind === 'edit') { await api.approve(selected, 'edited_approved', draftText); ctx.toast('Edited draft saved') }
      else if (kind === 'deny') { await api.deny(selected); ctx.toast('Denied, noted for style learning') }
      else if (kind === 'none') { await api.noResponse(selected); ctx.toast('Marked as no reply needed') }
    } catch (e) { ctx.toast(e.message, 'error') }
  }

  async function copy() {
    try {
      try { await navigator.clipboard.writeText(draftText) } catch { /* fallback below */ }
      await api.copyDraft(selected)
      ctx.toast('Copied to clipboard')
    } catch (e) { ctx.toast(e.message, 'error') }
  }

  const list = threads.filter(t => {
    if (filter === 'needs' && !t.needs_response_estimate) return false
    if (filter === 'risk' && t.priority_label !== 'risky_to_answer_fast') return false
    const q = query.trim().toLowerCase()
    if (!q) return true
    return `${t.contact_name || ''} ${t.latest_message || ''}`.toLowerCase().includes(q)
  })

  const counts = {
    needs: threads.filter(t => t.needs_response_estimate).length,
    all: threads.length,
    risk: threads.filter(t => t.priority_label === 'risky_to_answer_fast').length,
  }

  const riskFlags = draft ? (draft.risk_flags || (draft.risk_flags_json ? JSON.parse(draft.risk_flags_json) : [])) : []
  const isHighRisk = riskFlags.some(f => HIGH_RISK.includes(f))

  return (
    <div className={`inbox ${pane === 'detail' ? 'show-detail' : 'show-list'}`}>
      <div className="threads">
        <div className="threads-head">
          <h3>Threads</h3>
          <div className={`search${query ? ' has-value' : ''}`}>
            <Icon name="search" />
            <input
              type="search"
              placeholder="Search threads…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              aria-label="Search threads"
            />
            <button className="clear" onClick={() => setQuery('')} aria-label="Clear search"><Icon name="x" /></button>
          </div>
          <div className="filters">
            {[['needs', 'Needs reply'], ['all', 'All'], ['risk', 'Flagged']].map(([id, label]) => (
              <button key={id} className={`chip ${filter === id ? 'on' : ''}`} onClick={() => setFilter(id)} aria-pressed={filter === id}>
                {label}<span className="n">{counts[id]}</span>
              </button>
            ))}
          </div>
        </div>
        {loading && <div className="loading">Loading…</div>}
        {!loading && list.length === 0 && threads.length === 0 && (
          <div className="empty"><b>No threads yet.</b>Sync your messages to get started.</div>
        )}
        {!loading && list.length === 0 && threads.length > 0 && (
          <div className="threads-empty">Nothing matches that filter.</div>
        )}
        {list.map(t => (
          <div key={t.id} className={`thread ${selected === t.id ? 'active' : ''}`} onClick={() => loadThread(t.id)}>
            <div className="t-top"><span className="name">{t.contact_name}</span><span className="when">{fmtDate(t.latest_at)}</span></div>
            <div className="prev">{t.latest_message}</div>
            <div className="t-meta">
              {t.priority_label === 'urgent' && <span className="tag solid">Urgent</span>}
              {t.priority_label === 'risky_to_answer_fast' && <span className="tag flag">flagged</span>}
              {t.needs_response_estimate ? <span className="tag pop">Reply</span> : <span className="tag good">Caught up</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="detail">
        {!selected && <div className="empty">Select a thread to review</div>}
        {selected && thread && (
          <>
            <button className="mobile-back btn" onClick={() => setPane('list')}>‹ All threads</button>
            <div className="d-head">
              <div>
                <div className="eyebrow">{(thread.priority_label || '').replace(/_/g, ' ')}</div>
                <h2>{thread.contact_name}</h2>
                <div className="a-meta">
                  {thread.analytics && <span className="tag">{thread.analytics.emotional_tone} · {thread.analytics.confidence} conf</span>}
                  {riskFlags.map(f => <span key={f} className="tag flag">{f}</span>)}
                </div>
              </div>
              <button className="btn ghost" onClick={() => decide('none')}>No reply needed</button>
            </div>

            {thread.messages?.length > 0 && (
              <div className="d-pulse">
                <div className="ph">
                  <b>Last 14 days</b>
                  <span className="num">{openLabel(thread.messages)}</span>
                </div>
                <Pulse messages={thread.messages} />
                <PulseLegend />
              </div>
            )}

            <div className="convo">
              {thread.messages?.map(m => (
                <div key={m.id} className={`msg ${m.is_from_me ? 'me' : 'them'}`}>
                  <div className="bubble">{m.text}</div>
                  <div className="time">{fmtDate(m.created_at)}</div>
                </div>
              ))}
            </div>

            <hr className="rule-strong" />
            <div className="rw-label" style={{ marginTop: 0 }}>Draft reply</div>
            <div className="row between" style={{ marginBottom: 12 }}>
              <div className="reason" style={{ margin: 0 }}>
                {draft?.reason || 'Generate a reply suggestion for this thread.'}
                {draft?.mode === 'mock' && <span style={{ color: 'var(--muted)' }}> (offline draft — add an API key in Settings for smarter drafts)</span>}
              </div>
              <button className="btn primary" onClick={generate} disabled={busy} style={{ flexShrink: 0 }}>
                {busy ? '…' : draft ? 'Regenerate' : 'Generate draft'}
              </button>
            </div>

            {draft && (
              <>
                <div className="draft-card">
                  <textarea
                    value={draftText}
                    aria-label="Draft reply"
                    onChange={e => setDraftText(e.target.value)}
                    onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); copy() } }}
                  />
                  <div className="draft-foot">
                    <span>{words(draftText)}</span>
                    <span>⌘↵ to copy</span>
                  </div>
                </div>

                {isHighRisk && (
                  <div className="notice">
                    <Icon name="alert" />
                    <div>
                      <b>Read this one before you copy it.</b> The thread touches {riskFlags.join(', ').replace(/_/g, ' ')}.
                      ReplyGraph copies to your clipboard and stops there.
                    </div>
                  </div>
                )}
                {toneRisks?.flags?.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div className="flags">{toneRisks.flags.map(f => <span key={f} className="tag flag">{f.replace(/_/g, ' ')}</span>)}</div>
                    {toneRisks.suggestions?.[0] && <div className="sm" style={{ marginTop: 6, color: '#8a481c' }}>{toneRisks.suggestions[0]}</div>}
                  </div>
                )}

                <div className="rw-label">Rewrite</div>
                <div className="rewrites">
                  {REWRITES.map(([key, label]) => (
                    <button key={key} className="rw" disabled={busy} onClick={() => rewrite(key)}>{label}</button>
                  ))}
                </div>

                <div className="actions">
                  <button className="btn solid" onClick={() => decide('approve')}><Icon name="check" /> Approve</button>
                  <button className="btn" onClick={() => decide('edit')}>Save edit</button>
                  <button className="btn primary" onClick={copy}><Icon name="copy" /> Copy to clipboard</button>
                  <button className="btn ghost" onClick={() => decide('deny')}>Deny</button>
                </div>
              </>
            )}

            {thread.followups?.length > 0 && (
              <>
                <hr />
                <div className="sec-title">Follow-ups in this thread</div>
                <div className="panel">
                  {thread.followups.map(f => (
                    <div key={f.id} className="fu">
                      <div><div className="task">{f.task_text}</div>
                        <div className="fu-meta"><span className="dir">{(f.direction || '').replace(/_/g, ' ')}</span>{f.due_date && <span className="sm" style={{ color: 'var(--pop)' }}>Due: {f.due_date}</span>}<span className="conf">{f.confidence} conf</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function words(text) {
  const t = text || ''
  const n = t.trim() ? t.trim().split(/\s+/).length : 0
  return `${n} ${n === 1 ? 'word' : 'words'} · ${t.length} characters`
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}
