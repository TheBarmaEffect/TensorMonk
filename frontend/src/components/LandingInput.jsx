import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MicButton from './MicButton'
import SessionHistory from './SessionHistory'
import useVerdict from '../hooks/useVerdict'

const OUTPUT_FORMATS = [
  { id: 'executive', label: 'Executive', icon: '📋' },
  { id: 'technical', label: 'Technical', icon: '⚙️' },
  { id: 'legal', label: 'Legal', icon: '⚖️' },
  { id: 'investor', label: 'Investor', icon: '💼' },
]

const SUGGESTIONS = [
  "Should we pivot from B2B SaaS to a marketplace model?",
  "Is it the right time to raise a Series A at $15M valuation?",
  "Should we hire a CTO or outsource our MVP development?",
  "Should I accept the acquisition offer or keep growing?",
]

export default function LandingInput() {
  const [text, setText] = useState('')
  const [format, setFormat] = useState('executive')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [detectedDomain, setDetectedDomain] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const textareaRef = useRef(null)
  const domainDebounce = useRef(null)
  const { submit } = useVerdict()

  useEffect(() => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
    }
  }, [text])

  // Auto-detect domain and suggest format as user types
  useEffect(() => {
    if (domainDebounce.current) clearTimeout(domainDebounce.current)
    if (text.trim().length < 15) { setDetectedDomain(null); return }

    domainDebounce.current = setTimeout(() => {
      fetch('/api/verdict/detect-domain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim() }),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.domain) {
            setDetectedDomain(d)
            if (d.suggested_format) setFormat(d.suggested_format)
          }
        })
        .catch(() => {})
    }, 800)

    return () => clearTimeout(domainDebounce.current)
  }, [text])

  const handleSubmit = async () => {
    if (!text.trim() || isSubmitting) return
    setIsSubmitting(true)
    try {
      await submit(text.trim(), null, format)
    } catch (err) {
      console.error('Submit failed:', err)
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleTranscript = useCallback((t) => setText(t), [])

  return (
    <div className="h-full w-full flex flex-col items-center justify-center px-6 relative">
      {/* Session history button */}
      <div className="absolute top-4 right-4">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] border border-transparent hover:border-[var(--border)] transition"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          History
        </button>
        <AnimatePresence>
          {showHistory && <SessionHistory onClose={() => setShowHistory(false)} />}
        </AnimatePresence>
      </div>

      {/* Logo + Title */}
      <div className="text-center mb-10 fade-in-up">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-gold/10 flex items-center justify-center">
            <span className="text-gold text-lg">⚖</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">Verdict</h1>
        </div>
        <p className="text-[var(--text-muted)] text-sm">
          Multi-agent AI courtroom for adversarial decision analysis
        </p>
      </div>

      {/* Main input area */}
      <div className="w-full max-w-2xl fade-in-up-d1">
        <div className="rounded-2xl bg-[var(--bg-surface)] border border-[var(--border)] focus-within:border-[var(--border-hover)] transition-colors">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="What decision are you facing?"
            aria-label="Decision or question to evaluate"
            aria-describedby="input-help-text"
            className="w-full bg-transparent text-[var(--text-primary)] text-[15px] placeholder:text-[var(--text-muted)] resize-none outline-none px-5 pt-5 pb-2 min-h-[52px] max-h-[160px] leading-relaxed"
            rows={1}
          />

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between px-4 pb-3 pt-1">
            <div className="flex items-center gap-2">
              <MicButton onTranscript={handleTranscript} />

              {/* Format picker */}
              <div className="flex items-center gap-1 ml-1" role="radiogroup" aria-label="Output format">
                {OUTPUT_FORMATS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFormat(f.id)}
                    title={f.label}
                    role="radio"
                    aria-checked={format === f.id}
                    aria-label={`${f.label} format`}
                    className={`w-7 h-7 rounded-md flex items-center justify-center text-sm transition-all ${
                      format === f.id
                        ? 'bg-[var(--bg-elevated)] ring-1 ring-[var(--border-hover)]'
                        : 'hover:bg-[var(--bg-elevated)] opacity-50 hover:opacity-80'
                    }`}
                  >
                    {f.icon}
                  </button>
                ))}
              </div>
            </div>

            <motion.button
              onClick={handleSubmit}
              disabled={!text.trim() || isSubmitting}
              className="h-8 px-4 rounded-lg text-sm font-medium transition-all disabled:opacity-20"
              style={{
                background: text.trim() ? 'var(--gold)' : 'var(--bg-elevated)',
                color: text.trim() ? '#000' : 'var(--text-muted)',
              }}
              whileHover={text.trim() ? { scale: 1.03 } : {}}
              whileTap={text.trim() ? { scale: 0.97 } : {}}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analyzing
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  Submit
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </span>
              )}
            </motion.button>
          </div>
        </div>

        {/* Format label + detected domain */}
        <div className="flex items-center justify-center mt-3 gap-2">
          <span id="input-help-text" className="text-[11px] text-[var(--text-muted)]">
            Output: <span className="text-[var(--text-secondary)]">{OUTPUT_FORMATS.find(f => f.id === format)?.label}</span>
            <span className="mx-2 text-[var(--border)]">·</span>
            Press Enter to submit
          </span>
          <AnimatePresence>
            {detectedDomain && (
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-gold/10 text-gold border border-gold/20"
              >
                {detectedDomain.domain}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Suggestions */}
        <div className="mt-8 grid grid-cols-2 gap-2 fade-in-up-d2" role="list" aria-label="Example decisions">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => setText(s)}
              role="listitem"
              aria-label={`Use example: ${s}`}
              className="text-left px-4 py-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-hover)] hover:bg-[var(--bg-elevated)] text-[13px] text-[var(--text-secondary)] leading-snug transition-all"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Feature badges */}
        <div className="flex items-center justify-center gap-4 mt-8 fade-in-up-d3">
          {[
            { icon: '🤖', text: '6 AI Agents' },
            { icon: '⚡', text: 'Groq Llama 3.3' },
            { icon: '📊', text: 'Live Analytics' },
            { icon: '📥', text: 'Export Reports' },
          ].map((badge) => (
            <div key={badge.text} className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
              <span>{badge.icon}</span>
              {badge.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
