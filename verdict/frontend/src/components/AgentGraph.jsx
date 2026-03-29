import { useMemo } from 'react'
import AgentNode from './AgentNode'
import useVerdictStore from '../store/verdictStore'

const POS = {
  research:   { x: 50, y: 85 },
  prosecutor: { x: 20, y: 55 },
  defense:    { x: 80, y: 55 },
  judge:      { x: 50, y: 28 },
  synthesis:  { x: 50, y: 8 },
}
const WPOS = [{ x: 30, y: 40 }, { x: 50, y: 44 }, { x: 70, y: 40 }]
const CONNS = [
  { from: 'research', to: 'prosecutor', color: '#6b7280' },
  { from: 'research', to: 'defense', color: '#6b7280' },
  { from: 'prosecutor', to: 'judge', color: '#ef4444' },
  { from: 'defense', to: 'judge', color: '#3b82f6' },
  { from: 'judge', to: 'synthesis', color: '#f59e0b' },
]

function Line({ from, to, color, active }) {
  return <line x1={`${from.x}%`} y1={`${from.y}%`} x2={`${to.x}%`} y2={`${to.y}%`}
    stroke={color} strokeWidth="1" strokeDasharray="5 4" strokeOpacity={active ? 0.6 : 0.1}
    className={active ? 'dash-flow' : ''} />
}

export default function AgentGraph() {
  const a = useVerdictStore(s => s.agentStates)
  const isActive = (f, t) => {
    const from = a[f], to = a[t]
    if (!from || !to) return false
    return from.status === 'complete' || from.status === 'active' || to.status === 'active'
  }
  const wn = useMemo(() => a.witnesses.map((w, i) => ({ ...w, pos: WPOS[i] || WPOS[0] })), [a.witnesses])

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-3 left-0 right-0 text-center z-20">
        <span className="text-[9px] font-mono text-white/20 uppercase tracking-[0.2em]">Agent Network</span>
      </div>
      <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
        {CONNS.map((c, i) => <Line key={i} from={POS[c.from]} to={POS[c.to]} color={c.color} active={isActive(c.from, c.to)} />)}
        {wn.map((w, i) => <Line key={`w${i}`} from={POS.judge} to={w.pos} color="#a78bfa" active={w.status === 'active' || w.status === 'complete'} />)}
      </svg>
      <AgentNode agent="research" status={a.research.status} x={POS.research.x} y={POS.research.y} animationDelay={0} />
      <AgentNode agent="prosecutor" status={a.prosecutor.status} x={POS.prosecutor.x} y={POS.prosecutor.y} animationDelay={0.4} />
      <AgentNode agent="defense" status={a.defense.status} x={POS.defense.x} y={POS.defense.y} animationDelay={0.6} />
      <AgentNode agent="judge" status={a.judge.status} x={POS.judge.x} y={POS.judge.y} animationDelay={0.2} />
      <AgentNode agent="synthesis" status={a.synthesis.status} x={POS.synthesis.x} y={POS.synthesis.y} animationDelay={0.8} />
      {wn.map((w, i) => <AgentNode key={`w${i}`} agent="witness" status={w.status} x={w.pos.x} y={w.pos.y} animationDelay={0} />)}
    </div>
  )
}
