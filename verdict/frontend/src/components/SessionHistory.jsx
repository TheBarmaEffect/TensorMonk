import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function SessionHistory({ onClose }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/verdict/sessions/history')
      .then((r) => r.json())
      .then((data) => {
        setSessions(Array.isArray(data) ? data : data.sessions || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const rulingColor = (ruling) => {
    const r = (ruling || '').toLowerCase()
    if (r === 'proceed') return '#10b981'
    if (r === 'reject') return '#ef4444'
    return '#f59e0b'
  }

  const formatTime = (ts) => {
    if (!ts) return ''
    const d = new Date(ts)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return d.toLocaleDateString()
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="absolute top-14 right-4 w-80 max-h-[400px] overflow-y-auto rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] shadow-xl z-50"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
        <span className="text-[12px] font-semibold text-[var(--text-primary)]">Session History</span>
        <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-4 h-4 border-2 border-[var(--text-muted)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-8 px-4">
          <p className="text-[12px] text-[var(--text-muted)]">No previous sessions</p>
        </div>
      ) : (
        <div className="p-2 space-y-1">
          {sessions.map((s, i) => (
            <motion.div
              key={s.session_id || i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="px-3 py-2.5 rounded-lg hover:bg-[var(--bg-elevated)] transition cursor-pointer"
            >
              <p className="text-[12px] text-[var(--text-primary)] leading-snug line-clamp-2">
                {s.question || s.decision?.question || 'Untitled session'}
              </p>
              <div className="flex items-center gap-2 mt-1.5">
                {s.ruling && (
                  <span
                    className="text-[10px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded"
                    style={{ color: rulingColor(s.ruling), background: rulingColor(s.ruling) + '15' }}
                  >
                    {s.ruling}
                  </span>
                )}
                {s.domain && (
                  <span className="text-[10px] text-[var(--text-muted)] font-mono">{s.domain}</span>
                )}
                <span className="text-[10px] text-[var(--text-muted)] ml-auto">{formatTime(s.created_at)}</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
