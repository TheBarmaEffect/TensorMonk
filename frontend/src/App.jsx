/**
 * App.jsx — Root component for the Verdict AI Courtroom application.
 *
 * Wraps the application in an ErrorBoundary for crash recovery and
 * provides animated screen transitions between Landing and CourtRoom views.
 *
 * @module App
 */

import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import LandingInput from './components/LandingInput'
import CourtRoom from './components/CourtRoom'
import useVerdictStore from './store/verdictStore'

/**
 * ErrorBoundary — React class component that catches render errors.
 *
 * Displays a recovery UI with error details and a restart button
 * instead of crashing the entire application. Logs errors to console
 * for debugging.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('[Verdict ErrorBoundary]', error, errorInfo)
    this.setState({ errorInfo })
  }

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message || 'Unknown error'
      return (
        <div className="h-full w-full flex items-center justify-center bg-[var(--bg-primary)]" role="alert" aria-live="assertive">
          <div className="text-center max-w-md px-6">
            <div className="text-4xl mb-4" aria-hidden="true">⚠️</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Something went wrong</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-3">The courtroom hit an unexpected error.</p>
            <details className="mb-6 text-left">
              <summary className="text-[11px] text-[var(--text-muted)] cursor-pointer hover:text-[var(--text-secondary)] transition">
                Error details
              </summary>
              <pre className="mt-2 p-3 rounded-lg bg-[var(--bg-elevated)] text-[10px] text-red-400 font-mono overflow-auto max-h-32 border border-[var(--border)]">
                {errorMessage}
              </pre>
            </details>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => { this.setState({ hasError: false, error: null, errorInfo: null }) }}
                className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border)] transition-colors"
                aria-label="Dismiss error and try again"
              >
                Dismiss
              </button>
              <button
                onClick={() => { this.setState({ hasError: false }); window.location.reload() }}
                className="px-5 py-2 rounded-lg text-sm font-medium bg-gold text-black hover:bg-gold-light transition-colors shadow-sm"
                aria-label="Restart the application"
              >
                Restart
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

/**
 * AppContent — Main application layout with animated screen transitions.
 *
 * Uses Zustand store to determine current screen (landing vs courtroom)
 * and Framer Motion AnimatePresence for smooth crossfade transitions.
 */
function AppContent() {
  const screen = useVerdictStore((s) => s.screen)
  return (
    <div className="h-full w-full bg-[var(--bg-primary)] overflow-hidden" role="main">
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

/**
 * App — Root component wrapped in ErrorBoundary.
 * @returns {JSX.Element} The complete application
 */
export default function App() {
  return <ErrorBoundary><AppContent /></ErrorBoundary>
}
