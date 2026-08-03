import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Exports({ ctx }) {
  const [exports, setExports] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => { load() }, [])
  async function load() {
    try { setExports(await api.getExports()) }
    catch (e) { ctx.toast(e.message, 'error') }
    finally { setLoading(false) }
  }

  async function exportMarkdown() {
    setBusy(true)
    try { const r = await api.exportMarkdown(); ctx.toast(`Wrote ${r.files.length} markdown files`); await load() }
    catch (e) { ctx.toast(e.message, 'error') } finally { setBusy(false) }
  }
  async function exportObsidian() {
    setBusy(true)
    try {
      const r = await api.exportObsidian()
      if (r.ok) { ctx.toast(`Wrote ${r.files_written.length} files to vault`); await load() }
      else ctx.toast(r.error, 'error')
    } catch (e) { ctx.toast(e.message, 'error') } finally { setBusy(false) }
  }

  return (
    <div className="wrap">
      <div className="head"><div className="eyebrow">Output</div><h2>Exports</h2><p>Summaries only by default — never raw message dumps. User-triggered, timestamped, with confidence labels.</p></div>

      <div className="dash-cols">
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Markdown</h3>
          <p className="sm muted" style={{ margin: '10px 0 18px' }}>Daily digest, follow-ups, and analytics as local .md files in your export folder.</p>
          <button className="btn solid" onClick={exportMarkdown} disabled={busy}>{busy ? 'Exporting…' : 'Export Markdown'}</button>
        </div>
        <div className="card" style={{ padding: 22 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Obsidian</h3>
          <p className="sm muted" style={{ margin: '10px 0 18px' }}>Writes into /ReplyGraph/ with YAML frontmatter and [[wiki links]]. Set a vault path in Settings first.</p>
          <button className="btn solid" onClick={exportObsidian} disabled={busy}>{busy ? 'Exporting…' : 'Export to Obsidian'}</button>
        </div>
      </div>

      <div className="sec-title" style={{ marginTop: 30 }}>Recent exports</div>
      {loading && <div className="loading">Loading…</div>}
      {!loading && exports.length === 0 && <div className="empty">No exports yet.</div>}
      {exports.length > 0 && (
        <div className="panel">
          {exports.map(e => (
            <div key={e.id} className="fu">
              <div><span className="tag">{e.type}</span> <span className="sm muted" style={{ marginLeft: 8, wordBreak: 'break-all' }}>{e.path}</span></div>
              <span className="sm faint">{new Date(e.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
