import { useEffect, useRef } from 'react'

const AGENT_STYLES = {
  research: { label: 'Research Analyst', color: '#94a3b8', icon: '◎' },
  prosecutor: { label: 'Prosecutor', color: '#f43f5e', icon: '⚔' },
  defense: { label: 'Defense Counsel', color: '#3b82f6', icon: '⛨' },
  judge: { label: 'Judge', color: '#f59e0b', icon: '⚖' },
  witness_fact: { label: 'Fact Witness', color: '#a78bfa', icon: '◉' },
  witness_data: { label: 'Data Witness', color: '#a78bfa', icon: '◉' },
  witness_precedent: { label: 'Precedent Witness', color: '#a78bfa', icon: '◉' },
  synthesis: { label: 'Synthesis', color: '#10b981', icon: '✦' },
}

export default function AgentThinking({ agent, status, thinking, output }) {
  const style = AGENT_STYLES[agent] || AGENT_STYLES.research
  const isActive = status === 'active'
  const isComplete = status === 'complete'
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thinking])

  const renderOutput = () => {
    if (!output) return null

    if (output.opening) {
      return (
        <div className="mt-3 pt-3 border-t border-white/[0.04]">
          <p className="font-body text-[13px] text-white/80 font-light leading-relaxed mb-3">{output.opening}</p>
          {output.claims && (
            <div className="space-y-2">
              {output.claims.map((claim, i) => (
                <div key={i} className="rounded-lg bg-white/[0.02] border border-white/[0.04] p-3">
                  <p className="font-body text-xs font-medium text-white/70">{claim.statement}</p>
                  <p className="font-body text-[11px] text-white/30 mt-1.5 leading-relaxed">{claim.evidence?.slice(0, 180)}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <div className="h-[3px] flex-1 rounded-full bg-white/[0.06] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-1000 ease-out"
                        style={{ background: style.color, width: `${(claim.confidence || 0.5) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-white/25">{Math.round((claim.confidence || 0.5) * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (output.resolution) {
      return (
        <div className="mt-3 pt-3 border-t border-white/[0.04]">
          <span className={`inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded-md mb-2 ${
            output.verdict_on_claim === 'sustained' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
            output.verdict_on_claim === 'overruled' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
            'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            {output.verdict_on_claim}
          </span>
          <p className="font-body text-xs text-white/60 leading-relaxed font-light">{output.resolution}</p>
        </div>
      )
    }

    return null
  }

  return (
    <div
      className="glass rounded-xl overflow-hidden card-slide-in glass-shimmer"
      style={{ borderLeft: `2px solid ${style.color}20` }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 border-b border-white/[0.04]">
        <span className="text-sm" style={{ color: style.color }}>{style.icon}</span>
        <span className="font-body font-medium text-[13px] text-white/70">{style.label}</span>

        <span className={`ml-auto text-[9px] font-mono uppercase px-2 py-0.5 rounded-md tracking-wider ${
          isActive ? 'bg-white/[0.06] text-white/50' :
          isComplete ? 'bg-white/[0.03] text-white/25' :
          'bg-white/[0.02] text-white/15'
        }`}>
          {isActive ? 'analyzing' : isComplete ? 'done' : 'waiting'}
        </span>

        {isActive && (
          <div className="w-16 h-[2px] rounded-full overflow-hidden bg-white/[0.04]">
            <div
              className="h-full rounded-full animate-glow-pulse"
              style={{ background: `linear-gradient(90deg, transparent, ${style.color}, transparent)`, width: '60%', marginLeft: '20%' }}
            />
          </div>
        )}
      </div>

      {/* Content */}
      <div ref={scrollRef} className="px-4 py-3 max-h-[220px] overflow-y-auto">
        {thinking && (
          <p className={`font-mono text-[11px] leading-[1.7] ${isActive ? 'text-white/40 cursor-blink' : 'text-white/30'}`}>
            {thinking}
          </p>
        )}
        {renderOutput()}
      </div>
    </div>
  )
}
