import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import LandingInput from './components/LandingInput'
import CourtRoom from './components/CourtRoom'
import useVerdictStore from './store/verdictStore'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error('Verdict Error:', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full w-full flex items-center justify-center bg-[var(--bg-primary)]">
          <div className="text-center max-w-sm">
            <div className="text-4xl mb-4">⚠️</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Something went wrong</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-6">The courtroom hit an unexpected error.</p>
            <button
              onClick={() => { this.setState({ hasError: false }); window.location.reload() }}
              className="px-5 py-2 rounded-lg text-sm font-medium bg-[var(--bg-elevated)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] border border-[var(--border)] transition-colors"
            >
              Restart
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function AppContent() {
  const screen = useVerdictStore((s) => s.screen)
  return (
    <div className="h-full w-full bg-[var(--bg-primary)] overflow-hidden">
      <AnimatePresence mode="wait">
        {screen === 'landing' ? (
          <motion.div key="landing" className="h-full w-full"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.3 }}>
            <LandingInput />
          </motion.div>
        ) : (
          <motion.div key="courtroom" className="h-full w-full"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}>
            <CourtRoom />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function App() {
  return <ErrorBoundary><AppContent /></ErrorBoundary>
}
