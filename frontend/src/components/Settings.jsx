import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Settings({ ctx }) {
  const [s, setS] = useState(null)
  const [form, setForm] = useState({})
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getSettings().then(data => {
      setS(data)
      setForm({
        max_threads: data.max_threads,
        max_messages_per_thread: data.max_messages_per_thread,
        local_only_mode: data.local_only_mode,
        llm_model: data.llm_model,
        obsidian_vault_path: data.obsidian_vault_path || '',
        imessage_db_path: data.imessage_db_path || '',
      })
    }).catch(() => {})
  }, [])

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function save() {
    setSaving(true)
    try {
      const data = { ...form }
      if (apiKey.trim()) data.llm_api_key = apiKey.trim()
      await api.updateSettings(data)
      ctx.toast('Settings saved')
      ctx.refreshHealth()
      setApiKey('')
    } catch (e) { ctx.toast(e.message, 'error') } finally { setSaving(false) }
  }

  async function rebuild() {
    try { await api.rebuildAnalytics(); ctx.toast('Analytics rebuilt') }
    catch (e) { ctx.toast(e.message, 'error') }
  }
  async function resetDash() {
    try { await api.resetDashboardPrefs(); ctx.toast('Dashboard layout reset') }
    catch (e) { ctx.toast(e.message, 'error') }
  }

  if (!s) return <div className="wrap"><div className="loading">Loading settings…</div></div>

  const status = s.imessage_status || {}

  return (
    <div className="wrap">
      <div className="head row between">
        <div>
          <div className="eyebrow">Configuration</div><h2>Settings</h2>
          <p>All local. Nothing leaves your machine unless you add an API key and turn local-only mode off.</p>
        </div>
        <button className="btn primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
      </div>

      <Section title="iMessage">
        <Row label="Database status" desc={status.error || `Reading ${status.path || '~/Library/Messages/chat.db'} (read-only).`}>
          <span className={`tag ${status.accessible ? 'good' : ''}`}>{status.accessible ? 'Connected' : 'Not connected'}</span>
        </Row>
        <Row label="Database path" desc="Where ReplyGraph looks for your Messages database.">
          <input className="sinput" value={form.imessage_db_path} onChange={e => set('imessage_db_path', e.target.value)} />
        </Row>
        <Row label="Max threads" desc="How many recent conversations to pull per sync.">
          <input className="sinput" style={{ width: 90 }} type="number" value={form.max_threads} onChange={e => set('max_threads', Number(e.target.value))} />
        </Row>
        <Row label="Max messages / thread" desc="How far back to read in each conversation.">
          <input className="sinput" style={{ width: 90 }} type="number" value={form.max_messages_per_thread} onChange={e => set('max_messages_per_thread', Number(e.target.value))} />
        </Row>
        <Row label="Sync now" desc="Pull recent threads from the Messages database.">
          <button className="btn" onClick={ctx.sync} disabled={ctx.syncing}>{ctx.syncing ? 'Syncing…' : 'Sync Messages'}</button>
        </Row>
      </Section>

      <Section title="Privacy & LLM">
        <Row label="Local-only mode" desc="When on, drafts use offline heuristics and no message text is ever sent anywhere.">
          <Toggle on={form.local_only_mode} onClick={() => set('local_only_mode', !form.local_only_mode)} />
        </Row>
        <Row label="API key" desc={s.llm_api_key_set ? 'A key is stored locally. Enter a new one to replace it.' : 'Stored locally. Only used when local-only mode is off.'}>
          <input className="sinput" type="password" placeholder={s.llm_api_key_set ? '•••••• (set)' : 'sk-ant-…'} value={apiKey} onChange={e => setApiKey(e.target.value)} />
        </Row>
        <Row label="Model" desc="Stronger models for risky rewrites, cheaper ones for routine drafts.">
          <input className="sinput" style={{ width: 220 }} value={form.llm_model} onChange={e => set('llm_model', e.target.value)} />
        </Row>
      </Section>

      <Section title="Export">
        <Row label="Obsidian vault path" desc="Where /ReplyGraph/ notes get written.">
          <input className="sinput" placeholder="~/Documents/MyVault" value={form.obsidian_vault_path} onChange={e => set('obsidian_vault_path', e.target.value)} />
        </Row>
      </Section>

      <Section title="Data">
        <Row label="Rebuild analytics" desc="Recompute tone & relationship estimates from stored messages.">
          <button className="btn" onClick={rebuild}>Rebuild</button>
        </Row>
        <Row label="Reset dashboard layout" desc="Restore widgets, order and density to defaults.">
          <button className="btn" onClick={resetDash}>Reset</button>
        </Row>
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return <div className="ssection"><div className="sec-title">{title}</div><div className="card">{children}</div></div>
}
function Row({ label, desc, children }) {
  return (
    <div className="srow">
      <div><div className="s-label">{label}</div><div className="s-desc">{desc}</div></div>
      {children}
    </div>
  )
}
function Toggle({ on, onClick }) {
  return <div className={`tog ${on ? 'on' : ''}`} onClick={onClick} />
}
