import { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'
import { Icon } from './icons.jsx'
import Dashboard from './components/Dashboard.jsx'
import Inbox from './components/Inbox.jsx'
import FollowUps from './components/FollowUps.jsx'
import Analytics from './components/Analytics.jsx'
import Exports from './components/Exports.jsx'
import Settings from './components/Settings.jsx'

const TABS = [
  ['dashboard', 'Dashboard'],
  ['inbox', 'Inbox'],
  ['followups', 'Follow-ups'],
  ['analytics', 'Analytics'],
  ['exports', 'Exports'],
  ['settings', 'Settings'],
]
const MTAB = { dashboard: 'Home', inbox: 'Inbox', followups: 'Tasks', analytics: 'Stats', exports: 'Export', settings: 'Settings' }

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [inboxThread, setInboxThread] = useState(null)
  const [health, setHealth] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState(null)
  const [toasts, setToasts] = useState([])

  const toast = useCallback((msg, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2800)
  }, [])

  const refreshHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => {})
  }, [])

  useEffect(() => { refreshHealth() }, [refreshHealth])

  async function sync() {
    setSyncing(true)
    try {
      const result = await api.syncImessage()
      setSyncStatus(result)
      if (result.ok) toast(`Synced ${result.synced} threads`)
      else toast(result.error || 'Sync failed', 'error')
      refreshHealth()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSyncing(false)
    }
  }

  function openThread(id) {
    setInboxThread(id)
    setTab('inbox')
    window.scrollTo(0, 0)
  }

  function go(t) {
    setTab(t)
    if (t === 'inbox') setInboxThread(null)
    window.scrollTo(0, 0)
  }

  const imessageOk = health?.imessage?.accessible
  const ctx = { toast, openThread, go, sync, syncing, syncStatus, health, imessageOk, refreshHealth }

  return (
    <div className="app">
      <aside className="side">
        <div className="brand"><span className="mark"><span /></span><h1>Reply<b>Graph</b></h1></div>
        <nav className="nav">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => go(id)}>
              <Icon name={id} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="status">
            <span className="ring" style={{ background: imessageOk ? 'var(--good)' : 'var(--faint)' }} />
            {imessageOk ? 'iMessage connected' : 'iMessage not connected'}
          </div>
          <button className="sync" onClick={sync} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Sync Messages'}
          </button>
        </div>
      </aside>

      <main className="main">
        {tab !== 'inbox' && <Topbar imessageOk={imessageOk} syncStatus={syncStatus} onGo={go} />}
        {tab === 'dashboard' && <Dashboard ctx={ctx} />}
        {tab === 'inbox' && <Inbox ctx={ctx} initialThread={inboxThread} />}
        {tab === 'followups' && <FollowUps ctx={ctx} />}
        {tab === 'analytics' && <Analytics ctx={ctx} />}
        {tab === 'exports' && <Exports ctx={ctx} />}
        {tab === 'settings' && <Settings ctx={ctx} />}
      </main>

      <nav className="mobile-nav">
        {TABS.map(([id, label]) => (
          <button key={id} className={tab === id ? 'active' : ''} onClick={() => go(id)}>
            <Icon name={id} /><span>{MTAB[id] || label}</span>
          </button>
        ))}
      </nav>

      <div className="toasts">
        {toasts.map(t => <div key={t.id} className={`toast${t.type === 'error' ? ' toast-error' : ''}`}>{t.msg}</div>)}
      </div>
    </div>
  )
}

function Topbar({ imessageOk, syncStatus, onGo }) {
  if (imessageOk) {
    return (
      <div className="topbar">
        <span className="demo-pill" style={{ color: 'var(--good)', background: '#eafaf2' }}>CONNECTED</span>
        Reading your iMessages locally, read-only. Nothing is ever sent for you.
        {syncStatus?.ok && <> · {syncStatus.synced} threads synced</>}
      </div>
    )
  }
  return (
    <div className="topbar">
      <span className="demo-pill" style={{ color: 'var(--muted)', background: 'var(--panel)' }}>NOT CONNECTED</span>
      No iMessage access yet — grant Full Disk Access, then Sync.
      <span className="more" style={{ color: 'var(--pop)', cursor: 'pointer', fontWeight: 600 }} onClick={() => onGo('settings')}>&nbsp;Open Settings →</span>
    </div>
  )
}
