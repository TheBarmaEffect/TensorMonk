const AGENT_CONFIG = {
  research:   { color: '#6b7280', label: 'Research', icon: '🔍' },
  prosecutor: { color: '#ef4444', label: 'Prosecutor', icon: '⚔️' },
  defense:    { color: '#3b82f6', label: 'Defense', icon: '🛡️' },
  judge:      { color: '#f59e0b', label: 'Judge', icon: '⚖️' },
  witness:    { color: '#a78bfa', label: 'Witness', icon: '👁️' },
  synthesis:  { color: '#10b981', label: 'Synthesis', icon: '✨' },
}

export default function AgentNode({ agent, status = 'waiting', x, y, animationDelay = 0 }) {
  const c = AGENT_CONFIG[agent] || AGENT_CONFIG.research
  const isActive = status === 'active'
  const isComplete = status === 'complete'
  const isWaiting = status === 'waiting'

  return (
    <div className="absolute flex flex-col items-center gap-1.5 agent-node-pop"
      style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)', animationDelay: `${animationDelay}s` }}>
      <div className={`relative w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${isActive ? 'ring-pulse' : ''}`}
        style={{
          background: isWaiting ? 'rgba(255,255,255,0.03)' : c.color + '15',
          border: `1.5px solid ${isWaiting ? 'rgba(255,255,255,0.06)' : c.color + '40'}`,
          boxShadow: isActive ? `0 0 20px ${c.color}30` : isComplete ? `0 0 12px ${c.color}20` : 'none',
        }}>
        {isActive && <div className="absolute inset-[-3px] rounded-full border border-dashed spin-slow" style={{ borderColor: c.color + '30' }} />}
        {isComplete ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={c.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <span className="text-sm" style={{ opacity: isWaiting ? 0.25 : 0.85 }}>{c.icon}</span>
        )}
      </div>
      <span className="text-[8px] font-mono uppercase tracking-[0.1em] font-medium"
        style={{ color: isWaiting ? 'rgba(255,255,255,0.12)' : c.color + 'bb' }}>
        {c.label}
      </span>
    </div>
  )
}
