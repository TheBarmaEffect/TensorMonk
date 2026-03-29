import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import VerdictLogo from './VerdictLogo'
import MicButton from './MicButton'
import useVerdict from '../hooks/useVerdict'

export default function LandingInput() {
  const [text, setText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const textareaRef = useRef(null)
  const { submit } = useVerdict()

  useEffect(() => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
    }
  }, [text])

  const handleSubmit = async () => {
    if (!text.trim() || isSubmitting) return
    setIsSubmitting(true)
    await submit(text.trim())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleTranscript = useCallback((transcript) => {
    setText(transcript)
  }, [])

  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center px-6">
      {/* Ambient background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Main radial gradient */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[600px] rounded-full opacity-[0.07]"
          style={{ background: 'radial-gradient(ellipse, #f59e0b 0%, transparent 70%)' }} />
        {/* Red accent blob */}
        <div className="absolute w-[600px] h-[600px] rounded-full opacity-[0.04] blur-[100px] animate-blob-drift-1"
          style={{ background: 'radial-gradient(circle, #f43f5e 0%, transparent 70%)', top: '-15%', left: '-10%' }} />
        {/* Blue accent blob */}
        <div className="absolute w-[600px] h-[600px] rounded-full opacity-[0.04] blur-[100px] animate-blob-drift-2"
          style={{ background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)', bottom: '-15%', right: '-10%' }} />
        {/* Subtle grid */}
        <div className="absolute inset-0 opacity-[0.02]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '64px 64px' }} />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center max-w-xl w-full">
        {/* Logo */}
        <div className="mb-12 landing-fade-in">
          <VerdictLogo size="large" />
        </div>

        {/* Headline */}
        <div className="text-center mb-10 landing-fade-in-delay-1">
          <h2 className="font-display font-bold text-[2.75rem] leading-[1.1] tracking-tight text-white mb-4">
            What&apos;s your decision?
          </h2>
          <p className="font-body text-[var(--text-secondary)] text-base font-light tracking-wide">
            Bring the idea. We&apos;ll bring the argument.
          </p>
        </div>

        {/* Input card */}
        <div className="w-full landing-fade-in-delay-2">
          <div className="glass rounded-2xl p-1 glass-shimmer gradient-border">
            <div className="rounded-[14px] bg-[var(--bg-surface)]/50 p-4">
              <textarea
                ref={textareaRef}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your startup decision, product idea, or strategic choice..."
                className="w-full bg-transparent text-[var(--text-primary)] font-body text-[15px] font-light placeholder:text-[var(--text-muted)] resize-none outline-none min-h-[48px] max-h-[140px] leading-relaxed"
                rows={2}
              />

              {/* Controls */}
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.04]">
                <MicButton onTranscript={handleTranscript} />

                <motion.button
                  onClick={handleSubmit}
                  disabled={!text.trim() || isSubmitting}
                  className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl font-body font-medium text-sm transition-all duration-300 disabled:opacity-20 disabled:cursor-not-allowed"
                  style={{
                    background: text.trim()
                      ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                      : 'rgba(255,255,255,0.04)',
                    color: text.trim() ? '#050508' : 'rgba(255,255,255,0.2)',
                    boxShadow: text.trim() ? '0 0 20px rgba(245,158,11,0.2), 0 4px 12px rgba(0,0,0,0.3)' : 'none',
                  }}
                  whileHover={text.trim() ? { scale: 1.02, boxShadow: '0 0 30px rgba(245,158,11,0.3), 0 8px 24px rgba(0,0,0,0.4)' } : {}}
                  whileTap={text.trim() ? { scale: 0.98 } : {}}
                >
                  {isSubmitting ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Analyzing...
                    </span>
                  ) : (
                    <>
                      Submit to Court
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </>
                  )}
                </motion.button>
              </div>
            </div>
          </div>

          {/* Hint text */}
          <p className="text-center text-[var(--text-muted)] text-xs mt-4 font-light tracking-wide">
            Press Enter to submit · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
