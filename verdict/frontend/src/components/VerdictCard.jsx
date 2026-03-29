import { useEffect, useRef } from 'react'

const RULING_STYLES = {
  proceed: { color: '#10b981', bg: 'from-emerald-950/30 to-transparent', label: 'PROCEED' },
  reject: { color: '#f43f5e', bg: 'from-rose-950/30 to-transparent', label: 'REJECT' },
  conditional: { color: '#f59e0b', bg: 'from-amber-950/30 to-transparent', label: 'CONDITIONAL' },
}

function playGavelSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    osc.type = 'square'
    osc.frequency.setValueAtTime(120, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(50, ctx.currentTime + 0.12)
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25)
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.25)
  } catch { /* silent */ }
}

export default function VerdictCard({ verdict }) {
  const hasPlayed = useRef(false)
  const ruling = RULING_STYLES[verdict.ruling] || RULING_STYLES.conditional

  useEffect(() => {
    if (!hasPlayed.current) {
      hasPlayed.current = true
      setTimeout(playGavelSound, 400)
    }
  }, [])

  return (
    <div
      className={`glass rounded-xl overflow-hidden bg-gradient-to-b ${ruling.bg} verdict-card-enter`}
      style={{ borderLeft: `2px solid ${ruling.color}30` }}
    >
      <div className="px-5 py-5 border-b border-white/[0.04]">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-2 h-2 rounded-full" style={{ background: ruling.color, boxShadow: `0 0 12px ${ruling.color}40` }} />
          <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">Final Verdict</span>
        </div>

        <h2
          className="font-display font-bold text-4xl tracking-tight animate-gavel-shake"
          style={{ color: ruling.color }}
        >
          {ruling.label}
        </h2>

        {/* Confidence */}
        <div className="mt-5 flex items-center gap-3">
          <span className="text-[10px] font-mono text-white/20 uppercase tracking-wider">Confidence</span>
          <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-[1.5s] ease-out"
              style={{ background: `linear-gradient(90deg, ${ruling.color}80, ${ruling.color})`, width: `${verdict.confidence * 100}%` }}
            />
          </div>
          <span className="text-xs font-mono font-medium" style={{ color: ruling.color }}>
            {Math.round(verdict.confidence * 100)}%
          </span>
        </div>
      </div>

      <div className="px-5 py-4">
        <p className="font-body text-[13px] text-white/60 leading-[1.8] font-light">{verdict.reasoning}</p>

        {verdict.key_factors?.length > 0 && (
          <div className="mt-5 space-y-2.5">
            <h4 className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Key Factors</h4>
            {verdict.key_factors.map((factor, i) => (
              <div key={i} className="flex items-start gap-2.5 card-slide-in" style={{ animationDelay: `${0.3 + i * 0.1}s` }}>
                <span className="text-[10px] mt-0.5 font-mono" style={{ color: ruling.color }}>0{i+1}</span>
                <span className="text-xs text-white/50 font-body font-light leading-relaxed">{factor}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
