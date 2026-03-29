import { motion } from 'framer-motion'

/**
 * ComparisonMode — Side-by-side prosecution vs defense comparison view.
 *
 * Renders a two-column layout with aligned claims, confidence bars,
 * and visual indicators showing which side is stronger per claim.
 * Supports toggle between "summary" and "detailed" views.
 */

function ConfidenceBar({ value, color }) {
  return (
    <div className="w-full h-1.5 rounded-full bg-[var(--bg-elevated)] overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.round(value * 100)}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="h-full rounded-full"
        style={{ background: color }}
      />
    </div>
  )
}

function ClaimCard({ claim, color, index, side }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: side === 'left' ? -20 : 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="rounded-xl p-3 border border-[var(--border)] bg-[var(--bg-surface)]"
    >
      <p className="text-[12px] font-medium text-[var(--text-primary)] leading-relaxed mb-2">
        {claim.statement}
      </p>
      {claim.evidence && (
        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mb-2">
          {claim.evidence}
        </p>
      )}
      <div className="flex items-center gap-2">
        <ConfidenceBar value={claim.confidence || 0.5} color={color} />
        <span className="text-[10px] font-mono text-[var(--text-muted)] whitespace-nowrap">
          {Math.round((claim.confidence || 0.5) * 100)}%
        </span>
      </div>
    </motion.div>
  )
}

function SideHeader({ label, emoji, color, confidence }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <span className="text-lg">{emoji}</span>
        <span className="text-[13px] font-semibold" style={{ color }}>{label}</span>
      </div>
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full" style={{ background: `${color}15` }}>
        <span className="text-[10px] font-mono font-semibold" style={{ color }}>
          {Math.round((confidence || 0.5) * 100)}%
        </span>
      </div>
    </div>
  )
}

export default function ComparisonMode({ prosecutor, defense, witnesses = [] }) {
  if (!prosecutor && !defense) return null

  const proClaims = prosecutor?.claims || []
  const defClaims = defense?.claims || []
  const proConf = prosecutor?.confidence || 0.5
  const defConf = defense?.confidence || 0.5

  // Calculate which side is stronger
  const proScore = proClaims.reduce((sum, c) => sum + (c.confidence || 0.5), 0) / (proClaims.length || 1)
  const defScore = defClaims.reduce((sum, c) => sum + (c.confidence || 0.5), 0) / (defClaims.length || 1)

  // Witness verdicts summary
  const sustained = witnesses.filter(w => w.output?.verdict_on_claim === 'sustained').length
  const overruled = witnesses.filter(w => w.output?.verdict_on_claim === 'overruled').length
  const inconclusive = witnesses.filter(w => w.output?.verdict_on_claim === 'inconclusive').length

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="w-full max-w-4xl mx-auto"
    >
      {/* Strength indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono text-[#ef4444]">FOR {Math.round(proConf * 100)}%</span>
          <span className="text-[10px] text-[var(--text-muted)] font-medium">ARGUMENT STRENGTH</span>
          <span className="text-[11px] font-mono text-[#3b82f6]">{Math.round(defConf * 100)}% AGAINST</span>
        </div>
        <div className="flex h-2 rounded-full overflow-hidden bg-[var(--bg-elevated)]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(proConf / (proConf + defConf)) * 100}%` }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            className="h-full rounded-l-full"
            style={{ background: 'linear-gradient(90deg, #ef4444, #f87171)' }}
          />
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(defConf / (proConf + defConf)) * 100}%` }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            className="h-full rounded-r-full"
            style={{ background: 'linear-gradient(90deg, #60a5fa, #3b82f6)' }}
          />
        </div>
      </div>

      {/* Witness summary bar */}
      {witnesses.length > 0 && (
        <div className="flex items-center justify-center gap-4 mb-6 py-2 px-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)]">
          <span className="text-[10px] font-medium text-[var(--text-muted)]">WITNESS VERDICTS:</span>
          {sustained > 0 && (
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">{sustained} Sustained</span>
          )}
          {overruled > 0 && (
            <span className="text-[10px] font-mono text-red-400 bg-red-500/10 px-2 py-0.5 rounded">{overruled} Overruled</span>
          )}
          {inconclusive > 0 && (
            <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">{inconclusive} Inconclusive</span>
          )}
        </div>
      )}

      {/* Two-column comparison */}
      <div className="grid grid-cols-2 gap-6">
        {/* Prosecution side */}
        <div>
          <SideHeader label="Prosecution" emoji="⚔️" color="#ef4444" confidence={proConf} />
          {prosecutor?.opening && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-3 p-3 rounded-lg bg-[#ef44440a] border border-[#ef444418]"
            >
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed italic">
                "{prosecutor.opening}"
              </p>
            </motion.div>
          )}
          <div className="space-y-2.5">
            {proClaims.map((claim, i) => (
              <ClaimCard key={`pro-${i}`} claim={claim} color="#ef4444" index={i} side="left" />
            ))}
          </div>
          {prosecutor?.closing && (
            <p className="mt-3 text-[11px] text-[var(--text-muted)] italic leading-relaxed">
              {prosecutor.closing}
            </p>
          )}
        </div>

        {/* Defense side */}
        <div>
          <SideHeader label="Defense" emoji="🛡️" color="#3b82f6" confidence={defConf} />
          {defense?.opening && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-3 p-3 rounded-lg bg-[#3b82f60a] border border-[#3b82f618]"
            >
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed italic">
                "{defense.opening}"
              </p>
            </motion.div>
          )}
          <div className="space-y-2.5">
            {defClaims.map((claim, i) => (
              <ClaimCard key={`def-${i}`} claim={claim} color="#3b82f6" index={i} side="right" />
            ))}
          </div>
          {defense?.closing && (
            <p className="mt-3 text-[11px] text-[var(--text-muted)] italic leading-relaxed">
              {defense.closing}
            </p>
          )}
        </div>
      </div>

      {/* Score summary */}
      <div className="mt-6 flex items-center justify-center gap-6 py-3 px-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">Pro Claims:</span>
          <span className="text-[11px] font-mono font-semibold text-[#ef4444]">{proClaims.length}</span>
        </div>
        <div className="w-px h-4 bg-[var(--border)]" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">Avg Confidence:</span>
          <span className="text-[11px] font-mono font-semibold" style={{ color: proScore > defScore ? '#ef4444' : '#3b82f6' }}>
            {Math.round(proScore * 100)}% vs {Math.round(defScore * 100)}%
          </span>
        </div>
        <div className="w-px h-4 bg-[var(--border)]" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">Def Claims:</span>
          <span className="text-[11px] font-mono font-semibold text-[#3b82f6]">{defClaims.length}</span>
        </div>
      </div>
    </motion.div>
  )
}
