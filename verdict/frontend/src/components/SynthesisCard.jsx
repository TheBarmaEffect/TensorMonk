import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

function TypewriterText({ text, delay = 0, speed = 12 }) {
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

export default function SynthesisCard({ synthesis }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1, ease: 'easeOut' }}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.2 }}
        className="flex items-center gap-3 mb-5"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.4, delay: 0.4, type: 'spring', stiffness: 200 }}
          className="w-10 h-10 rounded-full flex items-center justify-center bg-emerald-500/10 border border-emerald-500/20"
        >
          <span className="text-lg">✨</span>
        </motion.div>
        <div>
          <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-[0.2em] mb-0.5">Final Synthesis</p>
          <h3 className="text-lg font-semibold text-emerald-400 tracking-tight">The Battle-Tested Version</h3>
        </div>
      </motion.div>

      {/* Improved idea — the main prose */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.8 }}
        className="relative pl-5 border-l-2 border-emerald-500/20 mb-6"
      >
        <p className="text-[14px] text-[var(--text-primary)] leading-[1.9] font-light whitespace-pre-line">
          <TypewriterText text={synthesis.improved_idea} delay={1000} speed={10} />
        </p>
      </motion.div>

      {/* Objections addressed — as natural narrative */}
      {synthesis.addressed_objections?.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 2 }}
          className="mb-6"
        >
          <p className="text-[11px] text-[var(--text-muted)] font-medium tracking-wide uppercase mb-3">How we addressed the objections</p>
          <div className="space-y-3">
            {synthesis.addressed_objections.map((o, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 2.3 + i * 0.3 }}
                className="flex items-start gap-3"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-1 flex-shrink-0 opacity-60">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <p className="text-[13px] text-[var(--text-secondary)] leading-[1.7]">{o}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recommended actions — as natural prose */}
      {synthesis.recommended_actions?.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 3.5 }}
        >
          <p className="text-[11px] text-[var(--text-muted)] font-medium tracking-wide uppercase mb-3">Recommended next steps</p>
          <div className="space-y-3">
            {synthesis.recommended_actions.map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 3.8 + i * 0.3 }}
                className="flex items-start gap-3"
              >
                <div className="w-1 h-1 rounded-full mt-2.5 flex-shrink-0 bg-emerald-500/40" />
                <p className="text-[13px] text-[var(--text-secondary)] leading-[1.7]">{a}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
