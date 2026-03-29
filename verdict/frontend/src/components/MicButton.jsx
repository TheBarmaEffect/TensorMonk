import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useRef } from 'react'
import useVoiceInput from '../hooks/useVoiceInput'

export default function MicButton({ onTranscript }) {
  const { isListening, transcript, startListening, stopListening, clearTranscript, supported } =
    useVoiceInput()
  const prevTranscript = useRef('')

  useEffect(() => {
    if (transcript && transcript !== prevTranscript.current) {
      prevTranscript.current = transcript
      onTranscript(transcript)
    }
  }, [transcript, onTranscript])

  if (!supported) return null

  const handleClick = () => {
    if (isListening) {
      stopListening()
    } else {
      clearTranscript()
      startListening()
    }
  }

  return (
    <motion.button
      onClick={handleClick}
      className="relative w-12 h-12 rounded-full glass flex items-center justify-center cursor-pointer"
      animate={{
        y: isListening ? 8 : 0,
        scale: isListening ? 1.1 : 1,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      whileHover={{ scale: isListening ? 1.1 : 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {/* Pulsing red ring when recording */}
      <AnimatePresence>
        {isListening && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-red-500"
            initial={{ scale: 1, opacity: 0 }}
            animate={{ scale: [1, 1.3, 1], opacity: [0.8, 0, 0.8] }}
            exit={{ scale: 1, opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </AnimatePresence>

      {/* Icon or visualizer bars */}
      {isListening ? (
        <div className="flex items-center gap-[3px] h-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.div
              key={i}
              className="w-[3px] bg-red-400 rounded-full"
              animate={{
                height: ['8px', `${12 + Math.random() * 10}px`, '8px'],
              }}
              transition={{
                duration: 0.4 + i * 0.1,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white/70">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      )}
    </motion.button>
  )
}
