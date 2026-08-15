/**
 * The pulse graph: two weeks of one thread on a single line.
 * Their messages tick above it, yours below, and the shaded stretch on the
 * right is everything since you last wrote back.
 */
const WINDOW = 14 * 24 * 60 // minutes
const reduceMotion = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function Pulse({ messages, height = 52, mini = false, window: win = WINDOW }) {
  const points = (messages || [])
    .map(m => ({ me: !!m.is_from_me, mins: (Date.now() - new Date(m.created_at).getTime()) / 60000 }))
    .filter(p => p.mins >= 0 && p.mins <= win)

  const W = 640
  const pad = 6
  const mid = height / 2
  const inner = W - pad * 2
  const up = mini ? 7 : 15
  const down = mini ? 6 : 13
  const x = mins => pad + (1 - Math.min(mins, win) / win) * inner

  const mine = points.filter(p => p.me).map(p => p.mins)
  const openSince = mine.length ? Math.min(...mine) : win
  const gapStart = x(openSince)
  const gapEnd = W - pad
  const gapWide = gapEnd - gapStart > 8
  const uid = `pulse-${Math.round(gapStart)}-${height}${mini ? 'm' : ''}`

  return (
    <svg
      className={`pulse${mini ? ' pulse-mini' : ''}`}
      viewBox={`0 0 ${W} ${height}`}
      preserveAspectRatio="none"
      style={mini ? undefined : { height: 'auto' }}
      role="img"
      aria-label={`Two weeks of this thread; ${label(openSince, win)}`}
    >
      <defs>
        <linearGradient id={uid} x1="0" x2="1">
          <stop offset="0" stopColor="var(--pop)" stopOpacity="0" />
          <stop offset="1" stopColor="var(--pop)" stopOpacity="0.16" />
        </linearGradient>
      </defs>

      <line className="axis" x1={pad} y1={mid} x2={W - pad} y2={mid} />

      {points.map((p, i) => {
        const px = x(p.mins)
        return p.me
          ? <line key={i} className="tick-me" x1={px} y1={mid + 2} x2={px} y2={mid + down} />
          : <line key={i} className="tick-them" x1={px} y1={mid - 2} x2={px} y2={mid - up} />
      })}

      {gapWide && (
        <>
          <rect className="gap-glow" x={gapStart} y={mid - up} width={gapEnd - gapStart} height={up + down} fill={`url(#${uid})`} />
          <line className="gap" x1={gapStart} y1={mid} x2={gapEnd - 3} y2={mid} />
        </>
      )}

      {!reduceMotion && !mini && <circle className="now-halo" cx={gapEnd} cy={mid} r="5" />}
      <circle className="now" cx={gapEnd} cy={mid} r={mini ? 2 : 3} />
    </svg>
  )
}

export function PulseLegend() {
  return (
    <div className="pulse-legend">
      <span style={{ color: 'var(--ink-2)' }}><i /> them</span>
      <span style={{ color: 'var(--faint)' }}><i /> you</span>
      <span style={{ color: 'var(--pop)' }}><i style={{ opacity: 0.6 }} /> waiting on you</span>
    </div>
  )
}

export function dur(mins) {
  if (mins < 60) return `${Math.round(mins)}m`
  if (mins < 60 * 36) return `${Math.round(mins / 60)}h`
  return `${Math.round(mins / 1440)}d`
}

export function openLabel(messages, win = WINDOW) {
  const mine = (messages || [])
    .filter(m => m.is_from_me)
    .map(m => (Date.now() - new Date(m.created_at).getTime()) / 60000)
    .filter(v => v >= 0)
  const openSince = mine.length ? Math.min(...mine) : Infinity
  return label(openSince, win)
}

function label(openSince, win) {
  return openSince >= win ? 'no reply in 14 days' : `${dur(openSince)} since you replied`
}
