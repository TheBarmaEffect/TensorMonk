import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

function playGavelSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    osc.type = 'square'
    osc.frequency.setValueAtTime(120, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(50, ctx.currentTime + 0.12)
    gain.gain.setValueAtTime(0.12, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25)
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.25)
  } catch {}
}

function TypewriterText({ text, delay = 0, speed = 15 }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !text) return
    ref.current.textContent = ''
    let i = 0
    const timer = setTimeout(() => {
      const iv = setInterval(() => {
        if (i < text.length) {
          ref.current.textContent += text[i]
          i++
        } else clearInterval(iv)
      }, speed)
      return () => clearInterval(iv)
    }, delay)
    return () => clearTimeout(timer)
  }, [text, delay, speed])
  return <span ref={ref} />
}

export default function VerdictCard({ verdict }) {
  const hasPlayed = useRef(false)
  const ruling = (verdict.ruling || 'conditional').toLowerCase()
  const rulingColor = ruling === 'proceed' ? '#10b981' : ruling === 'reject' ? '#ef4444' : '#f59e0b'
  const rulingLabel = ruling === 'proceed' ? 'Proceed' : ruling === 'reject' ? 'Reject' : 'Conditional Approval'

  useEffect(() => {
    if (!hasPlayed.current) { hasPlayed.current = true; setTimeout(playGavelSound, 600) }
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1.2, ease: 'easeOut' }}
    >
      {/* Judge's ruling header — dramatic entrance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.5, type: 'spring', stiffness: 200 }}
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: rulingColor + '15', border: `1.5px solid ${rulingColor}35` }}
          >
            <span className="text-lg">⚖️</span>
          </motion.div>
          <div>
            <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-[0.2em] mb-0.5">The Court's Ruling</p>
            <motion.h2
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="text-2xl font-semibold tracking-tight"
              style={{ color: rulingColor }}
            >
              {rulingLabel}
            </motion.h2>
          </div>
        </div>
      </motion.div>

      {/* The reasoning — presented as the judge speaking */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 1.2 }}
        className="relative pl-5 border-l-2 mb-6"
        style={{ borderColor: rulingColor + '30' }}
      >
        <p className="text-[14px] text-[var(--text-primary)] leading-[1.9] font-light">
          <TypewriterText text={verdict.reasoning} delay={1500} speed={12} />
        </p>
      </motion.div>

      {/* Key factors — presented as natural prose points, not a numbered list */}
      {verdict.key_factors?.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 2.5 }}
          className="space-y-3"
        >
          <p className="text-[11px] text-[var(--text-muted)] font-medium tracking-wide uppercase">Considerations that shaped this ruling</p>
          {verdict.key_factors.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 3 + i * 0.4 }}
              className="flex items-start gap-3"
            >
              <div className="w-1 h-1 rounded-full mt-2.5 flex-shrink-0" style={{ background: rulingColor + '60' }} />
              <p className="text-[13px] text-[var(--text-secondary)] leading-[1.7]">{f}</p>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
