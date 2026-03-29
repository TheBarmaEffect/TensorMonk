import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import VerdictLogo from './VerdictLogo'
import AgentGraph from './AgentGraph'
import AgentThinking from './AgentThinking'
import VerdictCard from './VerdictCard'
import SynthesisCard from './SynthesisCard'
import useVerdictStore from '../store/verdictStore'

function ElapsedTimer({ startTime }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startTime) return
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [startTime])

  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60

  return (
    <span className="font-mono text-xs text-white/30 tabular-nums">
      {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
    </span>
  )
}

export default function CourtRoom() {
  const { decision, agentStates, verdict, synthesis, startTime, feed, error } = useVerdictStore()
  const reset = useVerdictStore((s) => s.reset)
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [feed, verdict, synthesis])

  const showArguments =
    agentStates.prosecutor.status !== 'waiting' || agentStates.defense.status !== 'waiting'

  const isComplete = !!(verdict && synthesis)

  return (
    <div className="h-full w-full flex flex-col">
      {/* ─── Top Bar ─── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04] flex-shrink-0 bg-[var(--bg-void)]/80 backdrop-blur-xl z-10">
        <div className="flex items-center gap-4">
          {/* Back / New Decision button */}
          <motion.button
            onClick={reset}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/[0.04] transition-all duration-200 text-xs font-body"
            whileHover={{ x: -2 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            {isComplete ? 'New Decision' : 'Back'}
          </motion.button>

          <div className="h-4 w-px bg-white/[0.06]" />

          <p className="font-body text-xs text-white/35 max-w-[400px] truncate font-light">
            {decision?.question}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ElapsedTimer startTime={startTime} />
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/[0.08] border border-emerald-500/[0.12]">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-glow-pulse" />
            <span className="font-mono text-[10px] text-emerald-400/70 uppercase tracking-wider">Live</span>
          </div>
        </div>
      </div>

      {/* ─── Main Content ─── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left — Agent Graph */}
        <div className="w-[38%] border-r border-white/[0.04] flex-shrink-0 relative">
          <div className="absolute inset-0 bg-gradient-to-b from-[var(--bg-void)] via-transparent to-[var(--bg-void)] pointer-events-none z-10 opacity-30" />
          <AgentGraph />
        </div>

        {/* Right — Feed */}
        <div
          ref={feedRef}
          className="w-[62%] overflow-y-auto p-5 space-y-4"
        >
          {/* Error */}
          {error && (
            <div className="glass rounded-xl p-4 card-slide-in" style={{ borderLeft: '2px solid #f43f5e' }}>
              <p className="font-mono text-xs text-rose-400">{error}</p>
            </div>
          )}

          {/* Research */}
          {agentStates.research.status !== 'waiting' && (
            <AgentThinking
              agent="research"
              status={agentStates.research.status}
              thinking={agentStates.research.thinking}
              output={agentStates.research.output}
            />
          )}

          {/* Prosecutor + Defense */}
          {showArguments && (
            <div className="grid grid-cols-2 gap-3">
              {agentStates.prosecutor.status !== 'waiting' && (
                <AgentThinking
                  agent="prosecutor"
                  status={agentStates.prosecutor.status}
                  thinking={agentStates.prosecutor.thinking}
                  output={agentStates.prosecutor.output}
                />
              )}
              {agentStates.defense.status !== 'waiting' && (
                <AgentThinking
                  agent="defense"
                  status={agentStates.defense.status}
                  thinking={agentStates.defense.thinking}
                  output={agentStates.defense.output}
                />
              )}
            </div>
          )}

          {/* Judge */}
          {agentStates.judge.status !== 'waiting' && (
            <AgentThinking
              agent="judge"
              status={agentStates.judge.status}
              thinking={agentStates.judge.thinking}
              output={agentStates.judge.output}
            />
          )}

          {/* Witnesses */}
          {agentStates.witnesses.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              {agentStates.witnesses.map((w, i) => (
                <AgentThinking
                  key={`witness-${i}`}
                  agent={w.type}
                  status={w.status}
                  thinking={w.thinking}
                  output={w.output}
                />
              ))}
            </div>
          )}

          {/* Verdict */}
          {verdict && <VerdictCard verdict={verdict} />}

          {/* Synthesis */}
          {synthesis && <SynthesisCard synthesis={synthesis} />}

          {/* New Decision CTA at bottom */}
          {isComplete && (
            <div className="flex justify-center py-6">
              <motion.button
                onClick={reset}
                className="flex items-center gap-2.5 px-6 py-3 rounded-xl font-body text-sm font-medium text-white/50 hover:text-white/80 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.1] transition-all duration-300"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Start New Decision
              </motion.button>
            </div>
          )}

          {/* Empty state */}
          {agentStates.research.status === 'waiting' && !error && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center landing-fade-in">
                <div className="flex items-center justify-center gap-1.5 mb-3">
                  {[0, 0.15, 0.3].map((delay, i) => (
                    <div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full bg-amber-400/60 animate-glow-pulse"
                      style={{ animationDelay: `${delay}s` }}
                    />
                  ))}
                </div>
                <p className="font-body text-sm text-white/20 font-light">Preparing courtroom...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
