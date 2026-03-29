import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useRef } from 'react'
import useVoiceInput from '../hooks/useVoiceInput'

/**
 * Voice input button using the Web Speech API (SpeechRecognition).
 * Always rendered in the DOM for discoverability — shows a disabled state
 * with tooltip when the browser doesn't support speech recognition.
 * When active, displays an animated waveform and streams transcript text
 * back to the parent via onTranscript callback.
 */
export default function MicButton({ onTranscript }) {
  const { isListening, transcript, startListening, stopListening, clearTranscript, supported } = useVoiceInput()
  const prev = useRef('')

  useEffect(() => {
    if (transcript && transcript !== prev.current) {
      prev.current = transcript
      onTranscript(transcript)
    }
  }, [transcript, onTranscript])

  const handleClick = () => {
    if (!supported) return
    if (isListening) {
      stopListening()
    } else {
      clearTranscript()
      startListening()
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={!supported}
      title={supported ? (isListening ? 'Stop voice input' : 'Voice input (Web Speech API)') : 'Voice input not supported in this browser'}
      aria-label="Voice input"
      data-testid="voice-input-btn"
      className={`w-7 h-7 rounded-md flex items-center justify-center hover:bg-[var(--bg-elevated)] transition-all relative ${
        !supported ? 'opacity-30 cursor-not-allowed' : ''
      }`}
    >
      <AnimatePresence>
        {isListening && (
          <motion.div className="absolute inset-0 rounded-md border border-red-500/50"
            initial={{ scale: 1, opacity: 0 }} animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
            exit={{ opacity: 0 }} transition={{ duration: 1.5, repeat: Infinity }} />
        )}
      </AnimatePresence>
      {isListening ? (
        <div className="flex items-center gap-[2px] h-3.5">
          {[0,1,2].map(i => (
            <motion.div key={i} className="w-[2px] bg-red-400 rounded-full"
              animate={{ height: ['4px', `${8 + Math.random()*6}px`, '4px'] }}
              transition={{ duration: 0.4+i*0.1, repeat: Infinity }} />
          ))}
        </div>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--text-muted)]">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      )}
    </button>
  )
}
