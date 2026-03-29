import { motion } from 'framer-motion'

function CircularProgress({ score, size = 56 }) {
  const radius = (size - 6) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score)

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
        <circle
          cx={size/2} cy={size/2} r={radius}
          fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.16,1,0.3,1) 0.5s' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono text-xs font-bold text-emerald-400">{Math.round(score * 100)}</span>
      </div>
    </div>
  )
}

export default function SynthesisCard({ synthesis }) {
  const handleExport = () => {
    const blob = new Blob([JSON.stringify(synthesis, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'verdict-synthesis-report.json'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      className="glass rounded-xl overflow-hidden bg-gradient-to-b from-emerald-950/15 to-transparent synthesis-card-enter"
      style={{ borderLeft: '2px solid rgba(16,185,129,0.15)' }}
    >
      {/* Header */}
      <div className="px-5 py-5 border-b border-white/[0.04] flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400" style={{ boxShadow: '0 0 12px rgba(16,185,129,0.4)' }} />
            <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">Synthesis</span>
          </div>
          <h2 className="font-display font-bold text-xl text-emerald-400 tracking-tight">
            Battle-Tested Version
          </h2>
        </div>
        <CircularProgress score={synthesis.strength_score || 0.7} />
      </div>

      {/* Improved idea */}
      <div className="px-5 py-4 border-b border-white/[0.04]">
        <p className="font-body text-[13px] text-white/70 leading-[1.8] font-light whitespace-pre-line">
          {synthesis.improved_idea}
        </p>
      </div>

      {/* Objections */}
      {synthesis.addressed_objections?.length > 0 && (
        <div className="px-5 py-4 border-b border-white/[0.04]">
          <h4 className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-3">Objections Addressed</h4>
          <div className="space-y-2.5">
            {synthesis.addressed_objections.map((obj, i) => (
              <div key={i} className="card-slide-in" style={{ animationDelay: `${0.3 + i * 0.12}s` }}>
                <p className="font-body text-xs text-white/50 leading-relaxed font-light">{obj}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {synthesis.recommended_actions?.length > 0 && (
        <div className="px-5 py-4 border-b border-white/[0.04]">
          <h4 className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-3">Recommended Actions</h4>
          <ol className="space-y-2">
            {synthesis.recommended_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2.5 card-slide-in" style={{ animationDelay: `${0.6 + i * 0.1}s` }}>
                <span className="text-emerald-400/60 font-mono text-[11px] mt-px font-medium">{String(i+1).padStart(2,'0')}</span>
                <span className="font-body text-xs text-white/50 font-light leading-relaxed">{action}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Export */}
      <div className="px-5 py-4">
        <motion.button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-body text-xs font-medium text-emerald-400/70 bg-emerald-500/[0.06] border border-emerald-500/[0.1] hover:bg-emerald-500/[0.1] transition-all duration-200"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export Report
        </motion.button>
      </div>
    </div>
  )
}
