import { motion } from 'framer-motion'

const AGENT_CONFIG = {
  research:   { label: 'Research', color: '#6b7280', avatar: '🔍', side: 'center' },
  prosecutor: { label: 'Prosecutor', color: '#ef4444', avatar: '⚔️', side: 'left' },
  defense:    { label: 'Defense', color: '#3b82f6', avatar: '🛡️', side: 'right' },
  judge:      { label: 'Judge', color: '#f59e0b', avatar: '⚖️', side: 'center' },
  witness_fact: { label: 'Fact Witness', color: '#a78bfa', avatar: '👁️', side: 'center' },
  witness_data: { label: 'Data Witness', color: '#a78bfa', avatar: '📊', side: 'center' },
  witness_precedent: { label: 'Precedent Witness', color: '#a78bfa', avatar: '📜', side: 'center' },
  synthesis:  { label: 'Synthesis', color: '#10b981', avatar: '✨', side: 'center' },
  system:     { label: 'Court', color: '#666', avatar: '🏛️', side: 'center' },
}

function TypingIndicator({ color }) {
  return (
    <span className="typing-dots flex items-center gap-1" style={{ color }}>
      <span /><span /><span />
    </span>
  )
}

function ConfidenceBar({ value, color }) {
  if (value == null) return null
  return (
    <div className="flex items-center gap-2 mt-2">
      <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          style={{ background: color }}
        />
      </div>
      <span className="text-[10px] font-mono" style={{ color }}>{Math.round(value * 100)}%</span>
    </div>
  )
}

export default function ChatMessage({ agent, type = 'message', content, claims, thinking, isTyping, confidence, verdict_on_claim, delay = 0 }) {
  const config = AGENT_CONFIG[agent] || AGENT_CONFIG.system
  const isLeft = config.side === 'left'
  const isRight = config.side === 'right'
  const animClass = isLeft ? 'msg-in-left' : isRight ? 'msg-in-right' : 'msg-in'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`flex gap-3 max-w-[85%] ${isRight ? 'ml-auto flex-row-reverse' : ''} ${animClass}`}
    >
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-base"
        style={{ background: config.color + '18', border: `1.5px solid ${config.color}30` }}
      >
        {config.avatar}
      </div>

      {/* Bubble */}
      <div className="flex-1 min-w-0">
        {/* Name + badge */}
        <div className={`flex items-center gap-2 mb-1 ${isRight ? 'justify-end' : ''}`}>
          <span className="text-[11px] font-medium" style={{ color: config.color }}>{config.label}</span>
          {type === 'thinking' && (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-[var(--text-muted)] uppercase tracking-wider">analyzing</span>
          )}
          {verdict_on_claim && (
            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider ${
              verdict_on_claim === 'sustained' ? 'bg-emerald-500/10 text-emerald-400' :
              verdict_on_claim === 'overruled' ? 'bg-red-500/10 text-red-400' :
              'bg-amber-500/10 text-amber-400'
            }`}>
              {verdict_on_claim}
            </span>
          )}
        </div>

        {/* Content bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${isRight ? 'rounded-tr-md' : isLeft ? 'rounded-tl-md' : 'rounded-tl-md'}`}
          style={{
            background: isLeft ? config.color + '10' : isRight ? config.color + '10' : 'var(--bg-surface)',
            border: `1px solid ${config.color}15`,
          }}
        >
          {isTyping ? (
            <TypingIndicator color={config.color} />
          ) : (
            <>
              {/* Main content */}
              {content && (
                <p className="text-[13px] text-[var(--text-primary)] leading-[1.7] whitespace-pre-line">{content}</p>
              )}

              {/* Thinking phases */}
              {thinking && !content && (
                <div className="space-y-1">
                  {thinking.split('\n').filter(Boolean).map((line, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[10px] mt-0.5" style={{ color: config.color }}>→</span>
                      <p className="text-[12px] text-[var(--text-secondary)] leading-relaxed">{line}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Claims (prosecutor/defense) */}
              {claims && claims.length > 0 && (
                <div className="mt-3 space-y-2">
                  {claims.map((claim, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: isRight ? 8 : -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 * i }}
                      className="rounded-lg p-2.5"
                      style={{ background: 'rgba(255,255,255,0.03)', border: `1px solid ${config.color}10` }}
                    >
                      <p className="text-[12px] font-medium text-[var(--text-primary)] leading-snug">{claim.statement}</p>
                      <p className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">{claim.evidence?.slice(0, 150)}</p>
                      <ConfidenceBar value={claim.confidence} color={config.color} />
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Confidence bar for overall */}
              <ConfidenceBar value={confidence} color={config.color} />
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}
