/**
 * PipelineGraph — Visual representation of the LangGraph agent pipeline.
 *
 * Renders the verdict pipeline as a vertical flow diagram showing each
 * agent node, its status (pending/active/complete), and the edges between
 * them. Supports dynamic witness node rendering and confidence-based
 * routing path indicators.
 *
 * @module PipelineGraph
 */

import { motion } from 'framer-motion'

/** Node status colors and labels */
const STATUS_CONFIG = {
  pending: { color: '#6b7280', bg: '#6b728015', label: 'Pending' },
  active: { color: '#f59e0b', bg: '#f59e0b18', label: 'Running' },
  complete: { color: '#10b981', bg: '#10b98118', label: 'Complete' },
  error: { color: '#ef4444', bg: '#ef444418', label: 'Error' },
  waiting: { color: '#6b7280', bg: '#6b728015', label: 'Waiting' },
}

/** Agent icon mapping */
const AGENT_ICONS = {
  research: '🔍',
  prosecutor: '⚔️',
  defense: '🛡️',
  judge: '⚖️',
  witness_fact: '👁️',
  witness_data: '📊',
  witness_precedent: '📜',
  synthesis: '✨',
}

/**
 * Single pipeline node with status indicator and connection line.
 *
 * @param {Object} props
 * @param {string} props.label - Node display name
 * @param {string} props.status - Current node status
 * @param {string} props.icon - Emoji icon for the agent
 * @param {string} props.color - Accent color for the node
 * @param {boolean} props.isLast - Whether this is the last node (no connector line)
 * @param {number} props.delay - Animation delay in seconds
 */
function PipelineNode({ label, status, icon, color, isLast = false, delay = 0 }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay }}
      className="flex items-start gap-3"
    >
      {/* Node dot and connector line */}
      <div className="flex flex-col items-center">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center border-2 flex-shrink-0"
          style={{
            borderColor: config.color,
            background: config.bg,
          }}
        >
          <span className="text-sm">{icon}</span>
        </div>
        {!isLast && (
          <div
            className="w-0.5 h-6 mt-1"
            style={{ background: `${config.color}30` }}
          />
        )}
      </div>

      {/* Node label and status */}
      <div className="pt-1">
        <div className="flex items-center gap-2">
          <span
            className="text-[12px] font-medium"
            style={{ color: color || config.color }}
          >
            {label}
          </span>
          {status === 'active' && (
            <motion.div
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: config.color }}
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            />
          )}
          {status === 'complete' && (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={config.color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          )}
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">{config.label}</span>
      </div>
    </motion.div>
  )
}

/**
 * Parallel branch indicator — shows two nodes running side by side.
 *
 * @param {Object} props
 * @param {string} props.leftStatus - Status of the left (prosecutor) node
 * @param {string} props.rightStatus - Status of the right (defense) node
 * @param {number} props.delay - Animation delay
 */
function ParallelBranch({ leftStatus, rightStatus, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay }}
      className="flex items-start gap-6 pl-4"
    >
      <div className="flex-1">
        <PipelineNode
          label="Prosecutor"
          status={leftStatus}
          icon="⚔️"
          color="#ef4444"
          isLast
          delay={delay}
        />
      </div>
      <div className="w-px h-10 bg-[var(--border)] self-center" />
      <div className="flex-1">
        <PipelineNode
          label="Defense"
          status={rightStatus}
          icon="🛡️"
          color="#3b82f6"
          isLast
          delay={delay + 0.1}
        />
      </div>
    </motion.div>
  )
}

/**
 * PipelineGraph — Main pipeline visualization component.
 *
 * Renders the full verdict pipeline with proper ordering:
 * Research → [Prosecutor || Defense] → Judge → Witnesses → Verdict → Synthesis
 *
 * @param {Object} props
 * @param {Object} props.agentStates - Current state of all agents from Zustand store
 */
export default function PipelineGraph({ agentStates }) {
  if (!agentStates) return null

  const getStatus = (agent) => {
    const state = agentStates[agent]
    return state?.status || 'waiting'
  }

  const witnessStatuses = (agentStates.witnesses || []).map(w => ({
    type: w.type || 'witness_fact',
    status: w.status || 'waiting',
  }))

  const hasWitnesses = witnessStatuses.length > 0

  return (
    <div className="space-y-1 py-3" role="img" aria-label="Agent pipeline visualization">
      <PipelineNode
        label="Research Analyst"
        status={getStatus('research')}
        icon="🔍"
        color="#6b7280"
        delay={0}
      />

      <ParallelBranch
        leftStatus={getStatus('prosecutor')}
        rightStatus={getStatus('defense')}
        delay={0.1}
      />

      <PipelineNode
        label="Judge (Cross-Exam)"
        status={getStatus('judge')}
        icon="⚖️"
        color="#f59e0b"
        delay={0.2}
      />

      {hasWitnesses && witnessStatuses.map((w, i) => (
        <PipelineNode
          key={w.type + i}
          label={w.type.replace('witness_', '').replace(/^\w/, c => c.toUpperCase()) + ' Witness'}
          status={w.status}
          icon={AGENT_ICONS[w.type] || '👁️'}
          color="#a78bfa"
          delay={0.3 + i * 0.1}
        />
      ))}

      <PipelineNode
        label="Judge (Verdict)"
        status={getStatus('judge') === 'complete' && agentStates.synthesis?.status !== 'waiting' ? 'complete' : getStatus('judge')}
        icon="📜"
        color="#f59e0b"
        delay={0.4}
      />

      <PipelineNode
        label="Synthesis"
        status={getStatus('synthesis')}
        icon="✨"
        color="#10b981"
        isLast
        delay={0.5}
      />
    </div>
  )
}
