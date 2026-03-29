import { useEffect, useRef, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import VerdictCard from './VerdictCard'
import SynthesisCard from './SynthesisCard'
import FollowUp from './FollowUp'
import AnalyticsPanel from './AnalyticsPanel'
import ComparisonMode from './ComparisonMode'
import useVerdictStore from '../store/verdictStore'

/* ─── Safe parse helper ─── */
function safeParse(data) {
  if (!data) return null
  if (typeof data === 'object') return data
  try { return JSON.parse(data) } catch { return { summary: String(data) } }
}

/* ─── Agent Avatar ─── */
function AgentAvatar({ agent, size = 36 }) {
  const map = {
    research:   { emoji: '🔍', bg: '#6b728015', border: '#6b728040' },
    prosecutor: { emoji: '⚔️', bg: '#ef444418', border: '#ef444445' },
    defense:    { emoji: '🛡️', bg: '#3b82f618', border: '#3b82f645' },
    judge:      { emoji: '⚖️', bg: '#f59e0b18', border: '#f59e0b45' },
    witness_fact: { emoji: '👁️', bg: '#a78bfa18', border: '#a78bfa45' },
    witness_data: { emoji: '📊', bg: '#a78bfa18', border: '#a78bfa45' },
    witness_precedent: { emoji: '📜', bg: '#a78bfa18', border: '#a78bfa45' },
    synthesis:  { emoji: '✨', bg: '#10b98118', border: '#10b98145' },
  }
  const a = map[agent] || map.research
  return (
    <div className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, background: a.bg, border: `1.5px solid ${a.border}` }}>
      <span style={{ fontSize: size * 0.45 }}>{a.emoji}</span>
    </div>
  )
}

/* ─── Speech Bubble ─── */
function SpeechBubble({ agent, side, children, delay = 0 }) {
  const colors = {
    prosecutor: { bg: '#ef44440a', border: '#ef444418', text: '#ef4444', name: 'Prosecutor' },
    defense:    { bg: '#3b82f60a', border: '#3b82f618', text: '#3b82f6', name: 'Defense Counsel' },
    judge:      { bg: '#f59e0b08', border: '#f59e0b15', text: '#f59e0b', name: 'Judge' },
    research:   { bg: '#6b72800a', border: '#6b728018', text: '#6b7280', name: 'Research Analyst' },
    witness_fact: { bg: '#a78bfa08', border: '#a78bfa15', text: '#a78bfa', name: 'Fact Witness' },
    witness_data: { bg: '#a78bfa08', border: '#a78bfa15', text: '#a78bfa', name: 'Data Analyst' },
    witness_precedent: { bg: '#a78bfa08', border: '#a78bfa15', text: '#a78bfa', name: 'Precedent Expert' },
    synthesis:  { bg: '#10b98108', border: '#10b98115', text: '#10b981', name: 'Synthesis' },
  }
  const c = colors[agent] || colors.research
  const isLeft = side === 'left'
  const isRight = side === 'right'

  return (
    <motion.div
      initial={{ opacity: 0, x: isLeft ? -40 : isRight ? 40 : 0, y: isLeft || isRight ? 0 : 20 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`flex gap-3 ${isRight ? 'flex-row-reverse' : ''} ${isLeft || isRight ? 'max-w-[72%]' : 'max-w-[85%] mx-auto'} ${isRight ? 'ml-auto' : ''}`}
    >
      <AgentAvatar agent={agent} size={34} />
      <div className="flex-1 min-w-0">
        <div className={`flex items-center gap-2 mb-1.5 ${isRight ? 'justify-end' : ''}`}>
          <span className="text-[11px] font-semibold" style={{ color: c.text }}>{c.name}</span>
        </div>
        <div className={`rounded-2xl px-4 py-3 ${isLeft ? 'rounded-tl-md' : isRight ? 'rounded-tr-md' : 'rounded-tl-md'}`}
          style={{ background: c.bg, border: `1px solid ${c.border}` }}>
          {children}
        </div>
      </div>
    </motion.div>
  )
}

/* ─── Typing Indicator ─── */
function Typing({ agent, side }) {
  return (
    <SpeechBubble agent={agent} side={side}>
      <div className="flex items-center gap-1.5 py-1 px-1">
        {[0, 1, 2].map(i => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-current opacity-40"
            animate={{ opacity: [0.2, 0.7, 0.2], y: [0, -3, 0] }}
            transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }}
          />
        ))}
      </div>
    </SpeechBubble>
  )
}

/* ─── Court Announcement ─── */
function Announcement({ children, icon = '🏛️', color = 'var(--text-muted)', delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }} className="flex justify-center py-3">
      <div className="flex items-center gap-2.5 px-5 py-2.5 rounded-full border border-[var(--border)] bg-[var(--bg-surface)]">
        <span className="text-sm">{icon}</span>
        <span className="text-[11px] font-medium tracking-wide" style={{ color }}>{children}</span>
      </div>
    </motion.div>
  )
}

/* ─── Act Divider with dramatic stage transition ─── */
function ActDivider({ label, icon, actNumber, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, scaleX: 0 }}
      animate={{ opacity: 1, scaleX: 1 }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center gap-3 py-8 origin-center"
    >
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: '100%' }}
        transition={{ duration: 1.2, delay: delay + 0.2, ease: 'easeOut' }}
        className="flex-1 h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent"
      />
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: delay + 0.4 }}
        className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-[var(--bg-surface)] border border-[var(--border)]"
      >
        <span className="text-xs">{icon}</span>
        <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-[0.2em]">
          {actNumber && <span className="text-gold mr-1.5">Act {actNumber}</span>}
          {label}
        </span>
      </motion.div>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: '100%' }}
        transition={{ duration: 1.2, delay: delay + 0.2, ease: 'easeOut' }}
        className="flex-1 h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent"
      />
    </motion.div>
  )
}

/* ─── Timer ─── */
function Timer({ startTime }) {
  const [e, setE] = useState(0)
  useEffect(() => {
    if (!startTime) return
    const iv = setInterval(() => setE(Math.floor((Date.now() - startTime) / 1000)), 1000)
    return () => clearInterval(iv)
  }, [startTime])
  return <span className="font-mono text-[11px] text-[var(--text-muted)] tabular-nums">{String(Math.floor(e / 60)).padStart(2, '0')}:{String(e % 60).padStart(2, '0')}</span>
}

/* ─── Build the interleaved debate ─── */
function useDebateSequence(prosecutorOutput, defenseOutput) {
  return useMemo(() => {
    if (!prosecutorOutput && !defenseOutput) return []
    const sequence = []
    const proClaims = prosecutorOutput?.claims || []
    const defClaims = defenseOutput?.claims || []

    // Prosecutor opens
    if (prosecutorOutput?.opening) {
      sequence.push({ agent: 'prosecutor', side: 'left', type: 'opening', content: prosecutorOutput.opening })
    }

    // Defense opens (responds)
    if (defenseOutput?.opening) {
      sequence.push({ agent: 'defense', side: 'right', type: 'opening', content: defenseOutput.opening })
    }

    // Interleave claims — prosecutor makes a point, defense counters
    const maxClaims = Math.max(proClaims.length, defClaims.length)
    for (let i = 0; i < maxClaims; i++) {
      if (proClaims[i]) {
        sequence.push({ agent: 'prosecutor', side: 'left', type: 'claim', claim: proClaims[i] })
      }
      if (defClaims[i]) {
        sequence.push({ agent: 'defense', side: 'right', type: 'claim', claim: defClaims[i] })
      }
    }

    return sequence
  }, [prosecutorOutput, defenseOutput])
}

/* ─── Main CourtRoom ─── */
export default function CourtRoom() {
  const { decision, agentStates, verdict, synthesis, startTime, error, sessionId } = useVerdictStore()
  const reset = useVerdictStore(s => s.reset)
  const feedRef = useRef(null)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [showComparison, setShowComparison] = useState(false)
  const [visibleBubbles, setVisibleBubbles] = useState(0)
  const isComplete = !!(verdict && synthesis)

  const debateSequence = useDebateSequence(agentStates.prosecutor.output, agentStates.defense.output)

  // Slowly reveal debate bubbles one at a time for dramatic effect
  useEffect(() => {
    if (debateSequence.length === 0) { setVisibleBubbles(0); return }
    if (visibleBubbles >= debateSequence.length) return

    const timer = setTimeout(() => {
      setVisibleBubbles(prev => prev + 1)
    }, visibleBubbles === 0 ? 600 : 1800) // First bubble faster, then 1.8s between each

    return () => clearTimeout(timer)
  }, [debateSequence.length, visibleBubbles])

  // Auto-scroll
  useEffect(() => {
    if (feedRef.current) {
      setTimeout(() => {
        feedRef.current.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
      }, 100)
    }
  }, [visibleBubbles, agentStates, verdict, synthesis])

  const prosecutorDone = agentStates.prosecutor.status === 'complete'
  const defenseDone = agentStates.defense.status === 'complete'
  const debateStarted = agentStates.prosecutor.status !== 'waiting' || agentStates.defense.status !== 'waiting'
  const debateActive = agentStates.prosecutor.status === 'active' || agentStates.defense.status === 'active'

  return (
    <div className="h-full w-full flex flex-col bg-[var(--bg-primary)]">
      {/* ─── Top Bar ─── */}
      <div className="flex items-center justify-between px-5 h-12 border-b border-[var(--border)] flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={reset} className="flex items-center gap-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition text-[12px] font-medium">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            {isComplete ? 'New Decision' : 'Back'}
          </button>
          <div className="w-px h-4 bg-[var(--border)]" />
          <span className="text-gold text-sm">⚖</span>
          <p className="text-[12px] text-[var(--text-secondary)] max-w-[400px] truncate">{decision?.question}</p>
        </div>
        <div className="flex items-center gap-3">
          {isComplete && (
            <>
              <button onClick={() => { setShowComparison(!showComparison); if (showAnalytics) setShowAnalytics(false) }}
                className={`px-3 py-1 rounded-md text-[11px] font-medium transition ${showComparison ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'}`}>
                ⚖️ Compare
              </button>
              <button onClick={() => { setShowAnalytics(!showAnalytics); if (showComparison) setShowComparison(false) }}
                className={`px-3 py-1 rounded-md text-[11px] font-medium transition ${showAnalytics ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'}`}>
                📊 Analytics
              </button>
            </>
          )}
          <Timer startTime={startTime} />
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/15">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse" />
            <span className="text-[10px] text-emerald-400 font-mono">LIVE</span>
          </div>
        </div>
      </div>

      {/* ─── Main Area ─── */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div ref={feedRef} className="flex-1 overflow-y-auto px-6 md:px-10 py-6 space-y-4">

            {/* Error */}
            {error && (
              <div className="rounded-xl bg-red-500/8 border border-red-500/15 px-4 py-3 max-w-2xl mx-auto">
                <p className="text-[12px] text-red-400">⚠ {error}</p>
              </div>
            )}

            {/* ═══ ACT 1: INVESTIGATION ═══ */}
            {agentStates.research.status !== 'waiting' && (
              <>
                <Announcement icon="🏛️" color="var(--text-muted)" delay={0}>Court is now in session</Announcement>
                <ActDivider label="Investigation" icon="🔍" actNumber="I" delay={0.3} />

                {agentStates.research.status === 'active' ? (
                  <Typing agent="research" side="left" />
                ) : agentStates.research.output ? (() => {
                  const res = safeParse(agentStates.research.output)
                  return (
                    <SpeechBubble agent="research" side="left" delay={0.5}>
                      <p className="text-[13px] text-[var(--text-primary)] leading-[1.8]">
                        {res?.summary || res?.market_context || 'Research analysis complete.'}
                      </p>
                      {res?.key_data_points?.length > 0 && (
                        <div className="mt-3 space-y-1.5">
                          {res.key_data_points.slice(0, 4).map((p, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <div className="w-1 h-1 rounded-full bg-[var(--text-muted)] mt-2 flex-shrink-0" />
                              <span className="text-[12px] text-[var(--text-secondary)] leading-relaxed">{typeof p === 'string' ? p : JSON.stringify(p)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </SpeechBubble>
                  )
                })() : null}
              </>
            )}

            {/* ═══ ACT 2: THE DEBATE ═══ */}
            {debateStarted && (
              <>
                <ActDivider label="The Debate" icon="⚔️" actNumber="II" delay={0.2} />

                {/* Show typing indicators while agents are working */}
                {agentStates.prosecutor.status === 'active' && !agentStates.prosecutor.output && (
                  <Typing agent="prosecutor" side="left" />
                )}
                {agentStates.defense.status === 'active' && !agentStates.defense.output && (
                  <Typing agent="defense" side="right" />
                )}

                {/* Interleaved debate — revealed one bubble at a time */}
                {debateSequence.slice(0, visibleBubbles).map((item, i) => (
                  <SpeechBubble key={`debate-${i}`} agent={item.agent} side={item.side} delay={i === visibleBubbles - 1 ? 0.1 : 0}>
                    {item.type === 'opening' ? (
                      <p className="text-[13px] text-[var(--text-primary)] leading-[1.8]">{item.content}</p>
                    ) : (
                      <>
                        <p className="text-[13px] text-[var(--text-primary)] leading-[1.7] font-medium">{item.claim.statement}</p>
                        {item.claim.evidence && (
                          <p className="text-[12px] text-[var(--text-secondary)] mt-2 leading-relaxed">{item.claim.evidence}</p>
                        )}
                      </>
                    )}
                  </SpeechBubble>
                ))}

                {/* Show typing while more bubbles are coming */}
                {(prosecutorDone || defenseDone) && visibleBubbles < debateSequence.length && visibleBubbles > 0 && (
                  (() => {
                    const next = debateSequence[visibleBubbles]
                    return next ? <Typing agent={next.agent} side={next.side} /> : null
                  })()
                )}
              </>
            )}

            {/* ═══ ACT 3: CROSS-EXAMINATION ═══ */}
            {(agentStates.judge.status !== 'waiting' || agentStates.witnesses.some(w => w.status !== 'waiting')) && (
              <>
                <ActDivider label="Cross-Examination" icon="⚖️" actNumber="III" delay={0.3} />

                {agentStates.judge.status === 'active' && !agentStates.judge.output && (
                  <Typing agent="judge" side="left" />
                )}

                {agentStates.judge.output?.cross_examination_questions?.length > 0 && (
                  <SpeechBubble agent="judge" side="left" delay={0.3}>
                    <p className="text-[13px] text-[var(--text-primary)] leading-[1.8] mb-2">
                      The court has several questions that need to be addressed before rendering a judgment:
                    </p>
                    <div className="space-y-2">
                      {agentStates.judge.output.cross_examination_questions.map((q, i) => (
                        <p key={i} className="text-[12px] text-[var(--text-secondary)] leading-relaxed pl-3 border-l border-amber-500/20">
                          {typeof q === 'string' ? q : q.question || JSON.stringify(q)}
                        </p>
                      ))}
                    </div>
                  </SpeechBubble>
                )}

                {/* Witnesses testify */}
                {agentStates.witnesses.map((w, i) => (
                  w.status === 'active' ? (
                    <Typing key={`wt${i}`} agent={w.type || 'witness_fact'} side="left" />
                  ) : w.status === 'complete' && w.output ? (
                    <SpeechBubble key={`ws${i}`} agent={w.type || 'witness_fact'} side="left" delay={0.3 + i * 0.5}>
                      <div className="flex items-center gap-2 mb-2.5">
                        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md font-semibold tracking-wide ${
                          w.output.verdict_on_claim === 'sustained' ? 'bg-emerald-500/12 text-emerald-400' :
                          w.output.verdict_on_claim === 'overruled' ? 'bg-red-500/12 text-red-400' :
                          'bg-amber-500/12 text-amber-400'
                        }`}>{w.output.verdict_on_claim}</span>
                      </div>
                      <p className="text-[12px] text-[var(--text-primary)] leading-[1.8]">{w.output.resolution}</p>
                    </SpeechBubble>
                  ) : null
                ))}
              </>
            )}

            {/* ═══ ACT 4: THE RULING ═══ */}
            {verdict && (
              <>
                <ActDivider label="The Ruling" icon="📜" actNumber="IV" delay={0.3} />
                <Announcement icon="⚖️" color="#f59e0b" delay={0.6}>The Honorable Judge has reached a verdict</Announcement>
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 1, delay: 1.2, ease: [0.16, 1, 0.3, 1] }}
                  className="max-w-2xl mx-auto"
                >
                  <VerdictCard verdict={verdict} />
                </motion.div>
              </>
            )}

            {/* ═══ ACT 5: FINAL SYNTHESIS ═══ */}
            {synthesis && (
              <>
                <ActDivider label="Final Synthesis" icon="✨" actNumber="V" delay={0.3} />
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 1, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  className="max-w-2xl mx-auto"
                >
                  <SynthesisCard synthesis={synthesis} />
                </motion.div>
              </>
            )}

            {/* ═══ POST-TRIAL ═══ */}
            {isComplete && (
              <>
                <ActDivider label="Post-Trial" icon="💬" delay={0.2} />

                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                  className="flex items-center justify-center gap-3"
                >
                  <button onClick={() => {
                    fetch(`/api/verdict/${sessionId}/export/markdown`).then(r => r.text()).then(t => {
                      const b = new Blob([t], { type: 'text/markdown' }), u = URL.createObjectURL(b), a = document.createElement('a'); a.href = u; a.download = 'verdict-report.md'; a.click(); URL.revokeObjectURL(u)
                    })
                  }} className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border)] transition">
                    📄 Markdown
                  </button>
                  <button onClick={() => {
                    fetch(`/api/verdict/${sessionId}/export/pdf`).then(r => r.blob()).then(b => {
                      const u = URL.createObjectURL(b), a = document.createElement('a'); a.href = u; a.download = 'verdict-report.pdf'; a.click(); URL.revokeObjectURL(u)
                    })
                  }} className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border)] transition">
                    📑 PDF Report
                  </button>
                  <button onClick={() => {
                    fetch(`/api/verdict/${sessionId}/export/json`).then(r => r.text()).then(t => {
                      const b = new Blob([t], { type: 'application/json' }), u = URL.createObjectURL(b), a = document.createElement('a'); a.href = u; a.download = 'verdict-data.json'; a.click(); URL.revokeObjectURL(u)
                    })
                  }} className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-medium bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border)] transition">
                    📋 JSON
                  </button>
                </motion.div>

                <div className="max-w-2xl mx-auto">
                  <FollowUp sessionId={sessionId} />
                </div>

                <div className="flex justify-center py-8">
                  <motion.button onClick={reset} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-black bg-gold hover:bg-gold-light transition shadow-lg shadow-gold/20">
                    ⚖ Start New Decision
                  </motion.button>
                </div>
              </>
            )}

            {/* Waiting state */}
            {agentStates.research.status === 'waiting' && !error && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}>
                    <span className="text-4xl">⚖️</span>
                  </motion.div>
                  <p className="text-sm text-[var(--text-muted)] mt-4 tracking-wide">Assembling the courtroom...</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar panels — Analytics or Comparison */}
        <AnimatePresence>
          {showAnalytics && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 340, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="flex-shrink-0 border-l border-[var(--border)] bg-[var(--bg-secondary)] overflow-hidden"
            >
              <div className="w-[340px]">
                <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
                  <span className="text-[12px] font-medium text-[var(--text-primary)]">📊 Case Analytics</span>
                  <button onClick={() => setShowAnalytics(false)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
                  </button>
                </div>
                <AnalyticsPanel agentStates={agentStates} verdict={verdict} synthesis={synthesis} />
              </div>
            </motion.div>
          )}
          {showComparison && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 520, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="flex-shrink-0 border-l border-[var(--border)] bg-[var(--bg-secondary)] overflow-hidden overflow-y-auto"
            >
              <div className="w-[520px]">
                <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
                  <span className="text-[12px] font-medium text-[var(--text-primary)]">⚖️ Prosecution vs Defense — Side-by-Side</span>
                  <button onClick={() => setShowComparison(false)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
                  </button>
                </div>
                <div className="p-4">
                  <ComparisonMode
                    prosecutor={agentStates.prosecutor.output}
                    defense={agentStates.defense.output}
                    witnesses={agentStates.witnesses}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
