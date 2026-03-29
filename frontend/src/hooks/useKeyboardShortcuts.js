/**
 * useKeyboardShortcuts — Global keyboard shortcut handler for the Verdict app.
 *
 * Provides keyboard-driven navigation and actions for power users:
 * - Ctrl+Enter: Submit decision from landing page
 * - Escape: Return to landing page / close panels
 * - Ctrl+E: Export markdown report
 * - Ctrl+Shift+A: Toggle analytics panel
 * - Ctrl+Shift+C: Toggle comparison mode
 * - Ctrl+Shift+P: Toggle pipeline view
 *
 * Shortcuts are context-aware: submit only works on landing,
 * panel toggles only work in the courtroom after completion.
 *
 * @module useKeyboardShortcuts
 */

import { useEffect, useCallback } from 'react'

/**
 * Register global keyboard shortcuts.
 *
 * @param {Object} handlers - Map of action names to handler functions
 * @param {Function} [handlers.onSubmit] - Called on Ctrl+Enter
 * @param {Function} [handlers.onEscape] - Called on Escape
 * @param {Function} [handlers.onExportMarkdown] - Called on Ctrl+E
 * @param {Function} [handlers.onToggleAnalytics] - Called on Ctrl+Shift+A
 * @param {Function} [handlers.onToggleComparison] - Called on Ctrl+Shift+C
 * @param {Function} [handlers.onTogglePipeline] - Called on Ctrl+Shift+P
 * @param {boolean} [enabled=true] - Whether shortcuts are active
 */
export default function useKeyboardShortcuts(handlers = {}, enabled = true) {
  const handleKeyDown = useCallback(
    (event) => {
      if (!enabled) return

      // Don't trigger shortcuts when typing in inputs (except Ctrl combos)
      const target = event.target
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable

      const { key, ctrlKey, metaKey, shiftKey } = event
      const mod = ctrlKey || metaKey // Support both Ctrl (Windows) and Cmd (Mac)

      // Ctrl+Enter — Submit
      if (mod && key === 'Enter' && handlers.onSubmit) {
        event.preventDefault()
        handlers.onSubmit()
        return
      }

      // Escape — Back/Close (always works, even in inputs)
      if (key === 'Escape' && handlers.onEscape) {
        event.preventDefault()
        handlers.onEscape()
        return
      }

      // Skip remaining shortcuts if typing in an input
      if (isInput && !mod) return

      // Ctrl+E — Export markdown
      if (mod && key === 'e' && !shiftKey && handlers.onExportMarkdown) {
        event.preventDefault()
        handlers.onExportMarkdown()
        return
      }

      // Ctrl+Shift+A — Toggle analytics
      if (mod && shiftKey && key === 'A' && handlers.onToggleAnalytics) {
        event.preventDefault()
        handlers.onToggleAnalytics()
        return
      }

      // Ctrl+Shift+C — Toggle comparison
      if (mod && shiftKey && key === 'C' && handlers.onToggleComparison) {
        event.preventDefault()
        handlers.onToggleComparison()
        return
      }

      // Ctrl+Shift+P — Toggle pipeline
      if (mod && shiftKey && key === 'P' && handlers.onTogglePipeline) {
        event.preventDefault()
        handlers.onTogglePipeline()
        return
      }
    },
    [handlers, enabled]
  )

  useEffect(() => {
    if (!enabled) return

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown, enabled])
}
