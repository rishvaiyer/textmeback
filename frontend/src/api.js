const BASE = '/api'

async function req(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  health: () => req('GET', '/health'),
  syncImessage: () => req('POST', '/sync/imessage'),
  getThreads: () => req('GET', '/threads'),
  getThread: (id) => req('GET', `/threads/${id}`),
  generateDraft: (id) => req('POST', `/threads/${id}/draft`),
  rewriteDraft: (id, draft_text, rewrite_type, contact_tone = 'unknown') =>
    req('POST', `/threads/${id}/rewrite`, { draft_text, rewrite_type, contact_tone }),
  approve: (id, decision_type, edited_draft) =>
    req('POST', `/threads/${id}/approve`, { decision_type, edited_draft }),
  deny: (id) => req('POST', `/threads/${id}/deny`),
  noResponse: (id) => req('POST', `/threads/${id}/no-response`),
  copyDraft: (id) => req('POST', `/threads/${id}/copy`),
  pinThread: (id) => req('POST', `/threads/${id}/pin`),
  unpinThread: (id) => req('POST', `/threads/${id}/unpin`),
  pinContact: (id) => req('POST', `/contacts/${id}/pin`),
  unpinContact: (id) => req('POST', `/contacts/${id}/unpin`),
  getFollowups: () => req('GET', '/followups'),
  completeFollowup: (id) => req('POST', `/followups/${id}/complete`),
  getAnalytics: () => req('GET', '/analytics'),
  rebuildAnalytics: () => req('POST', '/analytics/rebuild'),
  getStyleProfile: () => req('GET', '/style-profile'),
  getDashboardPrefs: () => req('GET', '/dashboard/preferences'),
  setDashboardPrefs: (data) => req('POST', '/dashboard/preferences', { data }),
  resetDashboardPrefs: () => req('POST', '/dashboard/preferences/reset'),
  getExports: () => req('GET', '/exports'),
  exportMarkdown: () => req('POST', '/exports/markdown'),
  exportObsidian: () => req('POST', '/exports/obsidian'),
  getSettings: () => req('GET', '/settings'),
  updateSettings: (data) => req('POST', '/settings', { data }),
  getTokenUsage: () => req('GET', '/token-usage'),
}
