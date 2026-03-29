import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

const AGENT_STYLES = {
  research: { label: 'Research Analyst', color: 'var(--research-color)', bgClass: 'bg-research/5', icon: '🔍', borderColor: '#6b7a8d' },
  prosecutor: { label: 'Prosecutor', color: 'var(--prosecutor-color)', bgClass: 'bg-prosecutor/5', icon: '⚔️', borderColor: '#c0392b' },
  defense: { label: 'Defense Counsel', color: 'var(--defense-color)', bgClass: 'bg-defense/5', icon: '🛡️', borderColor: '#2472a4' },
  judge: { label: 'Judge', color: 'var(--judge-color)', bgClass: 'bg-judge/5', icon: '⚖️', borderColor: '#c9a962' },
  witness_fact: { label: 'Fact Witness', color: 'var(--witness-color)', bgClass: 'bg-witness/5', icon: '📋', borderColor: '#7c6f9c' },
  witness_data: { label: 'Data Witness', color: 'var(--witness-color)', bgClass: 'bg-witness/5', icon: '📊', borderColor: '#7c6f9c' },
  witness_precedent: { label: 'Precedent Witness', color: 'var(--witness-color)', bgClass: 'bg-witness/5', icon: '📜', borderColor: '#7c6f9c' },
  synthesis: { label: 'Synthesis', color: 'var(--synthesis-color)', bgClass: 'bg-synthesis/5', icon: '✨', borderColor: '#2d8659' },
}

function isJsonLike(str) {
  if (!str) return false
  const trimmed = str.trim()
  return (trimmed.startsWith('{') || trimmed.startsWith('"') || trimmed.startsWith('['))
}

function TypingDots({ color }) {
  return (
    <span className="typing-dots inline-flex gap-1">
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
    </span>
  )
}

function ConfidenceBar({ confidence, color }) {
  return (
    <div className="flex items-center gap-2 mt-2">
      <div className="h-[4px] flex-1 rounded-full bg-black/[0.04] overflow-hidden">
        <div
          className="h-full rounded-full progress-fill"
          style={{ background: color, width: `${(confidence || 0.5) * 100}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-[var(--text-muted)]">{Math.round((confidence || 0.5) * 100)}%</span>
    </div>
  )
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

  // Clean thinking text: filter out raw JSON
  const cleanThinking = (raw) => {
    if (!raw) return ''
    if (isJsonLike(raw)) return ''
    return raw
  }

  const renderOutput = () => {
    if (!output) return null

    // Prosecutor / Defense output (has opening + claims)
    if (output.opening) {
      return (
        <div className="mt-3 pt-3 border-t border-[var(--border-light)]">
          <p className="font-body text-[13px] text-navy/80 font-light leading-relaxed mb-3">{output.opening}</p>
          {output.claims && (
            <div className="space-y-2.5">
              {output.claims.map((claim, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-light)] p-3"
                >
                  <p className="font-body text-xs font-medium text-navy/80">{claim.statement}</p>
                  <p className="font-body text-[11px] text-[var(--text-secondary)] mt-1.5 leading-relaxed">{claim.evidence?.slice(0, 200)}</p>
                  <ConfidenceBar confidence={claim.confidence} color={style.borderColor} />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )
    }

    // Witness output (has resolution + verdict_on_claim)
    if (output.resolution) {
      return (
        <div className="mt-3 pt-3 border-t border-[var(--border-light)]">
          <span className={`inline-block text-[10px] font-mono uppercase px-2.5 py-1 rounded-md mb-2 font-medium ${
            output.verdict_on_claim === 'sustained' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
            output.verdict_on_claim === 'overruled' ? 'bg-red-50 text-red-700 border border-red-200' :
            'bg-amber-50 text-amber-700 border border-amber-200'
          }`}>
            {output.verdict_on_claim}
          </span>
          <p className="font-body text-xs text-[var(--text-secondary)] leading-relaxed font-light">{output.resolution}</p>
          <ConfidenceBar confidence={output.confidence} color={style.borderColor} />
        </div>
      )
    }

    // Research output (has summary + key_data_points, etc.)
    if (output.summary || output.market_context) {
      return (
        <div className="mt-3 pt-3 border-t border-[var(--border-light)]">
          {output.summary && (
            <p className="font-body text-[13px] text-navy/80 font-light leading-relaxed mb-3">{output.summary}</p>
          )}
          {output.key_data_points && output.key_data_points.length > 0 && (
            <div className="space-y-1.5 mt-2">
              <span className="font-body text-[10px] font-medium text-[var(--text-muted)] uppercase tracking-wider">Key Findings</span>
              {output.key_data_points.slice(0, 4).map((point, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-gold text-xs mt-0.5">•</span>
                  <span className="font-body text-[11px] text-[var(--text-secondary)] leading-relaxed">{point}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    // Judge output (has ruling + reasoning)
    if (output.ruling || output.reasoning) {
      return (
        <div className="mt-3 pt-3 border-t border-[var(--border-light)]">
          {output.ruling && (
            <span className={`inline-block text-[10px] font-mono uppercase px-2.5 py-1 rounded-md mb-2 font-medium ${
              output.ruling === 'proceed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
              output.ruling === 'reject' ? 'bg-red-50 text-red-700 border border-red-200' :
              'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              {output.ruling}
            </span>
          )}
          {output.reasoning && (
            <p className="font-body text-xs text-[var(--text-secondary)] leading-relaxed">{output.reasoning}</p>
          )}
          {output.confidence != null && (
            <ConfidenceBar confidence={output.confidence} color={style.borderColor} />
          )}
        </div>
      )
    }

    // Generic fallback - try to display nicely
    if (typeof output === 'object') {
      const displayFields = Object.entries(output).filter(([k, v]) =>
        typeof v === 'string' && v.length > 0 && !['id', 'decision_id', 'timestamp', 'agent'].includes(k)
      )
      if (displayFields.length > 0) {
        return (
          <div className="mt-3 pt-3 border-t border-[var(--border-light)] space-y-2">
            {displayFields.slice(0, 5).map(([key, value]) => (
              <div key={key}>
                <span className="font-body text-[10px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
                  {key.replace(/_/g, ' ')}
                </span>
                <p className="font-body text-xs text-[var(--text-secondary)] leading-relaxed mt-0.5">{String(value).slice(0, 300)}</p>
              </div>
            ))}
          </div>
        )
      }
    }

    return null
  }

  const displayThinking = cleanThinking(thinking)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="card rounded-xl overflow-hidden"
      style={{ borderLeft: `3px solid ${style.borderColor}20` }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-[var(--border-light)] bg-[var(--bg-secondary)]/40">
        <span className="text-base">{style.icon}</span>
        <span className="font-body font-semibold text-[13px] text-navy/80">{style.label}</span>

        <span className={`ml-auto text-[9px] font-mono uppercase px-2.5 py-1 rounded-md tracking-wider font-medium ${
          isActive ? 'bg-gold/10 text-gold-dark' :
          isComplete ? 'bg-emerald-50 text-emerald-600' :
          'bg-black/[0.03] text-[var(--text-light)]'
        }`}>
          {isActive ? 'analyzing' : isComplete ? 'complete' : 'waiting'}
        </span>

        {isActive && (
          <div className="w-20 h-[3px] rounded-full overflow-hidden bg-black/[0.04]">
            <div className="h-full rounded-full shimmer" style={{ background: style.borderColor, width: '100%', opacity: 0.6 }} />
          </div>
        )}
      </div>

      {/* Content */}
      <div ref={scrollRef} className="px-4 py-3 max-h-[280px] overflow-y-auto">
        {isActive && !displayThinking && (
          <div className="flex items-center gap-2.5">
            <TypingDots color={style.borderColor} />
            <span className="font-body text-xs text-[var(--text-muted)] italic">Analyzing...</span>
          </div>
        )}

        {displayThinking && (
          <div className="space-y-1">
            {displayThinking.split('\n').filter(Boolean).map((line, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-gold text-[10px] mt-0.5 font-mono">→</span>
                <p className={`font-body text-[12px] leading-[1.6] ${isActive ? 'text-[var(--text-secondary)]' : 'text-[var(--text-muted)]'}`}>
                  {line}
                </p>
              </div>
            ))}
            {isActive && <TypingDots color={style.borderColor} />}
          </div>
        )}

        {renderOutput()}
      </div>
    </motion.div>
  )
}
