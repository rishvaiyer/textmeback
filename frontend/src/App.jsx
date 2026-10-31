import { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'
import { Icon, currentTheme, toggleTheme } from './icons.jsx'
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
  const [theme, setTheme] = useState(currentTheme)

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
        <div className="brand"><span className="mark"><span /></span><h1>TextMe<b>Back</b></h1></div>
        <nav className="nav">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => go(id)}>
              <Icon name={id} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="trust">
            <span className={`ring${imessageOk ? '' : ' off'}`} />
            <div>
              <b>{imessageOk ? 'Local & read-only' : 'Not connected'}</b>
              <p>
                {imessageOk
                  ? <>Reads <span className="num">chat.db</span> on this Mac. Never writes, never sends.</>
                  : <>Grant Full Disk Access to your terminal, then sync.</>}
              </p>
            </div>
          </div>
          <button className="sync" onClick={sync} disabled={syncing}>
            {syncing && <Icon name="refresh" className="ic spin" />}
            {syncing ? 'Syncing…' : 'Sync messages'}
          </button>
        </div>
      </aside>

      <main className="main">
        {tab !== 'inbox' && (
          <Topbar
            imessageOk={imessageOk}
            syncStatus={syncStatus}
            onGo={go}
            theme={theme}
            onToggleTheme={() => setTheme(toggleTheme())}
          />
        )}
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

      <div className="toasts" role="status" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast${t.type === 'error' ? ' toast-error' : ''}`}>
            <Icon name={t.type === 'error' ? 'alert' : 'check'} />
            <span>{t.msg}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Topbar({ imessageOk, syncStatus, onGo, theme, onToggleTheme }) {
  const dark = theme === 'dark'
  return (
    <div className="topbar">
      <div className="note">
        {imessageOk ? (
          <>
            <span className="demo-pill" style={{ color: 'var(--good)', background: 'var(--good-soft)' }}>CONNECTED</span>
            <span className="txt">
              Reading your iMessages locally, read-only. Nothing is ever sent for you.
              {syncStatus?.ok && ` · ${syncStatus.synced} threads synced`}
            </span>
          </>
        ) : (
          <>
            <span className="demo-pill" style={{ color: 'var(--muted)', background: 'var(--panel)' }}>NOT CONNECTED</span>
            <span className="txt">No iMessage access yet. Grant Full Disk Access, then sync.</span>
            <span className="more" style={{ color: 'var(--pop)', cursor: 'pointer', fontWeight: 600 }} onClick={() => onGo('settings')}>Open settings</span>
          </>
        )}
      </div>
      <div className="spacer" />
      <div className="topbar-tools">
        <button
          className="iconbtn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}
          title="Theme"
        >
          <Icon name={dark ? 'sun' : 'moon'} />
        </button>
      </div>
    </div>
  )
}
