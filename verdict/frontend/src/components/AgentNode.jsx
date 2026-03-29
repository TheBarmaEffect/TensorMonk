const AGENT_CONFIG = {
  research: { color: '#94a3b8', glow: 'rgba(148,163,184,0.2)', label: 'Research', icon: '◎' },
  prosecutor: { color: '#f43f5e', glow: 'rgba(244,63,94,0.25)', label: 'Prosecutor', icon: '⚔' },
  defense: { color: '#3b82f6', glow: 'rgba(59,130,246,0.25)', label: 'Defense', icon: '⛨' },
  judge: { color: '#f59e0b', glow: 'rgba(245,158,11,0.25)', label: 'Judge', icon: '⚖' },
  witness: { color: '#a78bfa', glow: 'rgba(167,139,250,0.25)', label: 'Witness', icon: '◉' },
  synthesis: { color: '#10b981', glow: 'rgba(16,185,129,0.25)', label: 'Synthesis', icon: '✦' },
}

export default function AgentNode({ agent, status = 'waiting', x, y, animationDelay = 0 }) {
  const config = AGENT_CONFIG[agent] || AGENT_CONFIG.research
  const isActive = status === 'active'
  const isComplete = status === 'complete'
  const isWaiting = status === 'waiting'

  return (
    <div
      className="absolute flex flex-col items-center gap-1.5 agent-node-pop"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        transform: 'translate(-50%, -50%)',
        animationDelay: `${animationDelay}s`,
        transition: 'opacity 0.4s ease',
      }}
    >
      {/* Ring */}
      <div
        className={`relative w-11 h-11 rounded-full flex items-center justify-center transition-all duration-500 ${isActive ? 'animate-active-pulse' : ''}`}
        style={{
          background: isWaiting ? 'rgba(255,255,255,0.02)' : `${config.color}08`,
          border: `1.5px solid ${isWaiting ? 'rgba(255,255,255,0.06)' : config.color + '40'}`,
          boxShadow: isActive
            ? `0 0 24px ${config.glow}, 0 0 48px ${config.glow}`
            : isComplete
            ? `0 0 12px ${config.glow}`
            : 'none',
        }}
      >
        {isActive && (
          <div
            className="absolute inset-[-3px] rounded-full border border-dashed animate-spin-slow"
            style={{ borderColor: config.color + '50' }}
          />
        )}

        {isComplete ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={config.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <span className="text-sm" style={{ color: isWaiting ? 'rgba(255,255,255,0.1)' : config.color, opacity: isWaiting ? 0.4 : 0.9 }}>
            {config.icon}
          </span>
        )}
      </div>

      <span
        className="text-[9px] font-mono uppercase tracking-[0.12em] transition-colors duration-300"
        style={{ color: isWaiting ? 'rgba(255,255,255,0.1)' : config.color + '80' }}
      >
        {config.label}
      </span>
    </div>
  )
}
