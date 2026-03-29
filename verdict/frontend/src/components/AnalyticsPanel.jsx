import { useMemo } from 'react'
import { BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Cell, Tooltip } from 'recharts'

function StatCard({ label, value, color, icon }) {
  return (
    <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">{icon}</span>
        <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className="text-lg font-semibold" style={{ color }}>{value}</div>
    </div>
  )
}

export default function AnalyticsPanel({ agentStates, verdict, synthesis }) {
  const prosecutorData = agentStates.prosecutor.output
  const defenseData = agentStates.defense.output

  // Claim confidence comparison
  const claimData = useMemo(() => {
    const data = []
    const proClaims = prosecutorData?.claims || []
    const defClaims = defenseData?.claims || []
    const maxLen = Math.max(proClaims.length, defClaims.length)

    for (let i = 0; i < maxLen; i++) {
      data.push({
        name: `Claim ${i + 1}`,
        prosecution: proClaims[i]?.confidence ? Math.round(proClaims[i].confidence * 100) : 0,
        defense: defClaims[i]?.confidence ? Math.round(defClaims[i].confidence * 100) : 0,
      })
    }
    return data
  }, [prosecutorData, defenseData])

  // Radar data for overall comparison
  const radarData = useMemo(() => {
    if (!prosecutorData && !defenseData) return []
    return [
      { metric: 'Confidence', pro: Math.round((prosecutorData?.confidence || 0) * 100), def: Math.round((defenseData?.confidence || 0) * 100) },
      { metric: 'Evidence', pro: Math.round(((prosecutorData?.claims || []).reduce((a, c) => a + (c.confidence || 0), 0) / Math.max((prosecutorData?.claims || []).length, 1)) * 100), def: Math.round(((defenseData?.claims || []).reduce((a, c) => a + (c.confidence || 0), 0) / Math.max((defenseData?.claims || []).length, 1)) * 100) },
      { metric: 'Claims', pro: (prosecutorData?.claims || []).length * 25, def: (defenseData?.claims || []).length * 25 },
      { metric: 'Impact', pro: Math.round((prosecutorData?.confidence || 0.5) * 90), def: Math.round((defenseData?.confidence || 0.5) * 85) },
    ]
  }, [prosecutorData, defenseData])

  // Witness verdicts
  const witnessData = useMemo(() => {
    return agentStates.witnesses.filter(w => w.status === 'complete' && w.output).map(w => ({
      type: w.type.replace('witness_', '').charAt(0).toUpperCase() + w.type.replace('witness_', '').slice(1),
      verdict: w.output.verdict_on_claim,
      confidence: Math.round((w.output.confidence || 0.5) * 100),
    }))
  }, [agentStates.witnesses])

  const hasData = prosecutorData || defenseData || verdict

  if (!hasData) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center">
          <span className="text-2xl mb-3 block">📊</span>
          <p className="text-[12px] text-[var(--text-muted)]">Analytics will appear as agents complete their analysis</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-3 space-y-3 overflow-y-auto">
      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2">
        {verdict && (
          <StatCard
            label="Verdict"
            value={verdict.ruling?.toUpperCase() || '—'}
            color={verdict.ruling === 'proceed' ? '#10b981' : verdict.ruling === 'reject' ? '#ef4444' : '#f59e0b'}
            icon="⚖️"
          />
        )}
        {verdict && (
          <StatCard
            label="Confidence"
            value={`${Math.round((verdict.confidence || 0.5) * 100)}%`}
            color="var(--gold)"
            icon="📈"
          />
        )}
        {synthesis && (
          <StatCard
            label="Strength"
            value={`${Math.round((synthesis.strength_score || 0.7) * 100)}%`}
            color="#10b981"
            icon="💪"
          />
        )}
        <StatCard
          label="Witnesses"
          value={witnessData.length}
          color="#a78bfa"
          icon="👁️"
        />
      </div>

      {/* Claim confidence chart */}
      {claimData.length > 0 && (
        <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] p-3">
          <h4 className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium mb-3">Claim Confidence</h4>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={claimData} barGap={2}>
              <Tooltip
                contentStyle={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 11 }}
                itemStyle={{ color: '#a0a0a0' }}
              />
              <Bar dataKey="prosecution" radius={[3, 3, 0, 0]} maxBarSize={20}>
                {claimData.map((_, i) => <Cell key={i} fill="#ef4444" fillOpacity={0.7} />)}
              </Bar>
              <Bar dataKey="defense" radius={[3, 3, 0, 0]} maxBarSize={20}>
                {claimData.map((_, i) => <Cell key={i} fill="#3b82f6" fillOpacity={0.7} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex items-center justify-center gap-4 mt-1">
            <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]"><span className="w-2 h-2 rounded-sm bg-red-500/70" />Prosecution</span>
            <span className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]"><span className="w-2 h-2 rounded-sm bg-blue-500/70" />Defense</span>
          </div>
        </div>
      )}

      {/* Radar */}
      {radarData.length > 0 && (
        <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] p-3">
          <h4 className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium mb-2">Argument Comparison</h4>
          <ResponsiveContainer width="100%" height={160}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.06)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#666', fontSize: 10 }} />
              <Radar dataKey="pro" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={1.5} />
              <Radar dataKey="def" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={1.5} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Witness verdicts */}
      {witnessData.length > 0 && (
        <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] p-3">
          <h4 className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium mb-2">Witness Verdicts</h4>
          <div className="space-y-2">
            {witnessData.map((w, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-[12px] text-[var(--text-secondary)]">{w.type}</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className="h-full rounded-full progress-fill" style={{
                      width: `${w.confidence}%`,
                      background: w.verdict === 'sustained' ? '#10b981' : w.verdict === 'overruled' ? '#ef4444' : '#f59e0b'
                    }} />
                  </div>
                  <span className={`text-[9px] font-mono uppercase ${
                    w.verdict === 'sustained' ? 'text-emerald-400' : w.verdict === 'overruled' ? 'text-red-400' : 'text-amber-400'
                  }`}>
                    {w.verdict}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
