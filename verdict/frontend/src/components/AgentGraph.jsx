import { useMemo } from 'react'
import { motion } from 'framer-motion'
import AgentNode from './AgentNode'
import useVerdictStore from '../store/verdictStore'

const NODE_POSITIONS = {
  research:  { x: 50, y: 82 },
  prosecutor: { x: 22, y: 50 },
  defense:   { x: 78, y: 50 },
  judge:     { x: 50, y: 22 },
  synthesis:  { x: 50, y: 5 },
}

const WITNESS_POSITIONS = [
  { x: 35, y: 36 },
  { x: 50, y: 40 },
  { x: 65, y: 36 },
]

const CONNECTIONS = [
  { from: 'research', to: 'prosecutor', color: 'var(--research-color)' },
  { from: 'research', to: 'defense', color: 'var(--research-color)' },
  { from: 'prosecutor', to: 'judge', color: 'var(--prosecutor-color)' },
  { from: 'defense', to: 'judge', color: 'var(--defense-color)' },
  { from: 'judge', to: 'synthesis', color: 'var(--judge-color)' },
]

function ConnectionLine({ from, to, color, isActive }) {
  const x1 = from.x
  const y1 = from.y
  const x2 = to.x
  const y2 = to.y

  return (
    <line
      x1={`${x1}%`} y1={`${y1}%`}
      x2={`${x2}%`} y2={`${y2}%`}
      stroke={color}
      strokeWidth="1.5"
      strokeDasharray="6 4"
      strokeOpacity={isActive ? 0.8 : 0.15}
      className={isActive ? 'animate-dash-flow' : ''}
    />
  )
}

export default function AgentGraph() {
  const agentStates = useVerdictStore((s) => s.agentStates)

  const isConnectionActive = (fromAgent, toAgent) => {
    const from = fromAgent === 'research' ? agentStates.research : agentStates[fromAgent]
    const to = toAgent === 'synthesis' ? agentStates.synthesis : agentStates[toAgent]
    if (!from || !to) return false
    return from.status === 'active' || from.status === 'complete' || to.status === 'active'
  }

  const witnessNodes = useMemo(() => {
    return agentStates.witnesses.map((w, i) => ({
      ...w,
      position: WITNESS_POSITIONS[i] || WITNESS_POSITIONS[0],
    }))
  }, [agentStates.witnesses])

  return (
    <div className="relative w-full h-full">
      {/* SVG connection lines */}
      <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
        {CONNECTIONS.map((conn, i) => (
          <ConnectionLine
            key={i}
            from={NODE_POSITIONS[conn.from]}
            to={NODE_POSITIONS[conn.to]}
            color={conn.color}
            isActive={isConnectionActive(conn.from, conn.to)}
          />
        ))}

        {/* Witness connection lines */}
        {witnessNodes.map((w, i) => (
          <ConnectionLine
            key={`witness-${i}`}
            from={NODE_POSITIONS.judge}
            to={w.position}
            color="var(--witness-color)"
            isActive={w.status === 'active' || w.status === 'complete'}
          />
        ))}
      </svg>

      {/* Agent nodes */}
      <AgentNode agent="research" status={agentStates.research.status} x={NODE_POSITIONS.research.x} y={NODE_POSITIONS.research.y} animationDelay={0} />
      <AgentNode agent="prosecutor" status={agentStates.prosecutor.status} x={NODE_POSITIONS.prosecutor.x} y={NODE_POSITIONS.prosecutor.y} animationDelay={0.5} />
      <AgentNode agent="defense" status={agentStates.defense.status} x={NODE_POSITIONS.defense.x} y={NODE_POSITIONS.defense.y} animationDelay={0.7} />
      <AgentNode agent="judge" status={agentStates.judge.status} x={NODE_POSITIONS.judge.x} y={NODE_POSITIONS.judge.y} animationDelay={0.3} />
      <AgentNode agent="synthesis" status={agentStates.synthesis.status} x={NODE_POSITIONS.synthesis.x} y={NODE_POSITIONS.synthesis.y} animationDelay={0.9} />

      {/* Dynamic witness nodes */}
      {witnessNodes.map((w, i) => (
        <AgentNode
          key={`witness-${i}`}
          agent="witness"
          status={w.status}
          x={w.position.x}
          y={w.position.y}
          animationDelay={0}
        />
      ))}
    </div>
  )
}
