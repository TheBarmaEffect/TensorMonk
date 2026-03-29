import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function FollowUp({ sessionId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef(null)
  const chatRef = useRef(null)

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages])

  const askQuestion = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res = await fetch(`/api/verdict/${sessionId}/followup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!res.ok) throw new Error('Failed to get response')
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I couldn\'t process that question. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      askQuestion()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] overflow-hidden mt-4"
    >
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-2">
        <span className="text-sm">💬</span>
        <span className="text-[12px] font-medium text-[var(--text-primary)]">Ask Follow-up Questions</span>
        <span className="text-[10px] text-[var(--text-muted)] ml-1">— powered by the same AI agents</span>
      </div>

      {/* Messages */}
      {messages.length > 0 && (
        <div ref={chatRef} className="max-h-[300px] overflow-y-auto px-4 py-3 space-y-3">
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-gold/15 text-gold-light rounded-br-md'
                    : 'bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded-bl-md'
                }`}>
                  <p className="text-[13px] leading-[1.6] whitespace-pre-line">{msg.content}</p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <div className="flex justify-start">
              <div className="bg-[var(--bg-elevated)] rounded-2xl rounded-bl-md px-4 py-3">
                <span className="typing-dots text-[var(--text-muted)]"><span /><span /><span /></span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <div className="px-3 pb-3 pt-2">
        <div className="flex items-center gap-2 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)] px-3 py-2 focus-within:border-[var(--border-hover)] transition-colors">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the verdict, specific claims, or next steps..."
            className="flex-1 bg-transparent text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none"
          />
          <button
            onClick={askQuestion}
            disabled={!input.trim() || loading}
            className="w-7 h-7 rounded-lg flex items-center justify-center bg-gold/20 text-gold hover:bg-gold/30 disabled:opacity-20 transition-all"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 2L11 13" /><path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </div>
      </div>
    </motion.div>
  )
}
