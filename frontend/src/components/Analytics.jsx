import { useState, useEffect } from 'react'
import { api } from '../api.js'

const TREND = { declining: '↓ higher-friction lately', improving: '↑ warming up', stable: '→ stable', shifting: '~ shifting' }

export default function Analytics({ ctx }) {
  const [data, setData] = useState([])
  const [tokens, setTokens] = useState(null)
  const [loading, setLoading] = useState(true)
  const [rebuilding, setRebuilding] = useState(false)

  useEffect(() => {
    Promise.all([api.getAnalytics(), api.getTokenUsage()])
      .then(([a, t]) => { setData(a); setTokens(t) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function rebuild() {
    setRebuilding(true)
    try { await api.rebuildAnalytics(); setData(await api.getAnalytics()); ctx.toast('Analytics rebuilt') }
    catch (e) { ctx.toast(e.message, 'error') }
    finally { setRebuilding(false) }
  }

  if (loading) return <div className="wrap"><div className="loading">Loading analytics…</div></div>

  return (
    <div className="wrap">
      <div className="head row between">
        <div>
          <div className="eyebrow">Estimates</div><h2>Analytics</h2>
          <p>Heuristic estimates from text patterns — not facts, not psychology. Confidence shows how much data was available.</p>
        </div>
        <button className="btn" onClick={rebuild} disabled={rebuilding}>{rebuilding ? 'Rebuilding…' : '↻ Rebuild'}</button>
      </div>

      <div className="notice" style={{ marginBottom: 22 }}>
        These are <b>estimates</b>. Low confidence means take it lightly. ReplyGraph describes threads ("higher-friction lately") — it does not judge people.
      </div>

      {data.length === 0 && <div className="empty">No analytics yet. Sync messages, then rebuild.</div>}

      {data.map((a, i) => (
        <div key={i} className="card acard">
          <div className="a-top">
            <div>
              <div className="a-name">{a.contact_name}</div>
              <div className="a-meta">
                <span className="tag">{a.emotional_tone}</span>
                <span className="sm muted">{TREND[a.tone_trend] || a.tone_trend}</span>
                <span className="conf">{a.confidence} conf</span>
              </div>
            </div>
            <div className="sm muted" style={{ textAlign: 'right' }}>
              {a.message_volume} messages{a.last_interaction && <><br />{new Date(a.last_interaction).toLocaleDateString()}</>}
            </div>
          </div>
          <div className="stats">
            {a.avg_response_hours != null && <Stat k="Avg response" v={`~${a.avg_response_hours}h`} />}
            <Stat k="You're waiting" v={a.user_waiting_on_them ? 'Yes' : 'No'} />
            {a.common_topics?.length > 0 && <Stat k="Topics" v={a.common_topics.join(', ')} />}
            {a.open_loops?.length > 0 && <Stat k="Open loop" v={a.open_loops[0].slice(0, 38) + '…'} pop />}
          </div>
        </div>
      ))}

      {tokens?.by_operation?.length > 0 && (
        <>
          <div className="sec-title" style={{ marginTop: 32 }}>Token usage estimate</div>
          <div className="card" style={{ padding: 20 }}>
            <table>
              <thead><tr><th>Operation</th><th>Runs</th><th>Input</th><th>Output</th><th>Est. cost</th></tr></thead>
              <tbody>
                {tokens.by_operation.map((r, i) => (
                  <tr key={i}>
                    <td>{r.operation}</td>
                    <td className="muted">{r.count}</td>
                    <td className="muted">{r.total_input_tokens?.toLocaleString()}</td>
                    <td className="muted">{r.total_output_tokens?.toLocaleString()}</td>
                    <td style={{ color: 'var(--pop)', fontWeight: 700 }}>${r.estimated_cost_usd?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="sm muted" style={{ marginTop: 12 }}>Prices come from your editable settings and may not match real billing.</p>
          </div>
        </>
      )}
    </div>
  )
}

function Stat({ k, v, pop }) {
  return <div className="stat"><div className="k">{k}</div><div className="v" style={pop ? { fontSize: 12.5, color: 'var(--pop)' } : { fontSize: 13 }}>{v}</div></div>
}
