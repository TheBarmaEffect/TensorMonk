/**
 * useVerdict — Core hook for WebSocket-based verdict session management.
 *
 * Handles:
 * - REST session creation via POST /api/verdict/start
 * - WebSocket connection with automatic reconnection and exponential backoff
 * - Event dispatching to Zustand store for real-time agent state updates
 * - Graceful disconnect and error recovery
 *
 * @returns {Object} Session state, submit/disconnect functions, agent states
 */

import { useCallback, useRef } from 'react'
import useVerdictStore from '../store/verdictStore'

const API_BASE = '/api/verdict'

/** Maximum number of WebSocket reconnection attempts before giving up. */
const MAX_RECONNECT_ATTEMPTS = 5

/** Base delay in ms for exponential backoff (doubles each attempt). */
const BASE_RECONNECT_DELAY = 1000

// WebSocket connects directly to backend (Vercel rewrites don't proxy WS).
// In production, VITE_WS_URL points to the HF Space backend; locally it
// uses the same host as the page (Vite proxy handles it).
const WS_BACKEND = import.meta.env.VITE_WS_URL || ''

/**
 * Construct the WebSocket URL for a given session.
 * @param {string} sessionId - The verdict session UUID
 * @returns {string} Full WebSocket URL (wss:// or ws://)
 */
function getWsUrl(sessionId) {
  if (WS_BACKEND) {
    const protocol = WS_BACKEND.startsWith('https') ? 'wss:' : 'ws:'
    const host = WS_BACKEND.replace(/^https?:\/\//, '')
    return `${protocol}//${host}${API_BASE}/${sessionId}/stream`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${API_BASE}/${sessionId}/stream`
}

export default function useVerdict() {
  const wsRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef(null)
  const sessionIdRef = useRef(null)
  const {
    sessionId,
    agentStates,
    feed,
    verdict,
    synthesis,
    error,
    screen,
    decision,
    startTime,
    startSession,
    updateAgent,
    addFeedItem,
    setVerdict,
    setSynthesis,
    setError,
  } = useVerdictStore()

  /**
   * Handle incoming WebSocket events and dispatch to store.
   * @param {Object} event - Parsed StreamEvent from backend
   */
  const handleEvent = useCallback(
    (event) => {
      const { event_type, agent, content, data } = event

      // Add to feed
      addFeedItem({ event_type, agent, content, data })

      // Update agent states based on event type
      switch (event_type) {
        case 'research_start':
          updateAgent('research', { status: 'active', thinking: (useVerdictStore.getState().agentStates.research.thinking || '') + (content || '') })
          break
        case 'research_complete':
          updateAgent('research', { status: 'complete', output: data })
          break
        case 'prosecutor_thinking':
          updateAgent('prosecutor', { status: 'active', thinking: (useVerdictStore.getState().agentStates.prosecutor.thinking || '') + (content || '') })
          break
        case 'prosecutor_complete':
          updateAgent('prosecutor', { status: 'complete', output: data })
          break
        case 'defense_thinking':
          updateAgent('defense', { status: 'active', thinking: (useVerdictStore.getState().agentStates.defense.thinking || '') + (content || '') })
          break
        case 'defense_complete':
          updateAgent('defense', { status: 'complete', output: data })
          break
        case 'judge_start':
          updateAgent('judge', { status: 'active', thinking: (useVerdictStore.getState().agentStates.judge.thinking || '') + (content || '') })
          break
        case 'witness_spawned':
          if (agent) {
            updateAgent(agent, { status: 'active', thinking: content || '', data })
          }
          break
        case 'witness_complete':
          if (agent) {
            updateAgent(agent, { status: 'complete', output: data })
          }
          break
        case 'cross_examination_complete':
          updateAgent('judge', { thinking: (useVerdictStore.getState().agentStates.judge.thinking || '') + '\n' + (content || '') })
          break
        case 'verdict_start':
          updateAgent('judge', { thinking: (useVerdictStore.getState().agentStates.judge.thinking || '') + '\n' + (content || '') })
          break
        case 'verdict_complete':
          updateAgent('judge', { status: 'complete', output: data })
          setVerdict(data)
          break
        case 'synthesis_start':
          updateAgent('synthesis', { status: 'active', thinking: (useVerdictStore.getState().agentStates.synthesis.thinking || '') + (content || '') })
          break
        case 'synthesis_complete':
          updateAgent('synthesis', { status: 'complete', output: data })
          setSynthesis(data)
          break
        case 'error':
          setError(content)
          break
        case 'pipeline_complete':
          // Reset reconnect counter on successful completion
          reconnectAttemptsRef.current = 0
          break
        default:
          break
      }
    },
    [updateAgent, addFeedItem, setVerdict, setSynthesis, setError]
  )

  /**
   * Connect (or reconnect) a WebSocket for the given session ID.
   * Implements exponential backoff with jitter on failure.
   * @param {string} sid - Session ID to connect to
   */
  const connectWebSocket = useCallback(
    (sid) => {
      if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) {
        return // Already connected or connecting
      }

      const ws = new WebSocket(getWsUrl(sid))
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[useVerdict] WebSocket connected')
        reconnectAttemptsRef.current = 0 // Reset on successful connection
      }

      ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data)
          handleEvent(event)
        } catch (err) {
          console.error('[useVerdict] Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (e) => {
        console.error('[useVerdict] WebSocket error:', e)
      }

      ws.onclose = (e) => {
        console.log(`[useVerdict] WebSocket closed (code=${e.code}, reason=${e.reason})`)

        // Don't reconnect if intentionally closed (1000) or pipeline complete
        if (e.code === 1000 || !sessionIdRef.current) {
          return
        }

        // Attempt reconnection with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const attempt = reconnectAttemptsRef.current
          const delay = BASE_RECONNECT_DELAY * Math.pow(2, attempt)
          const jitter = Math.random() * delay * 0.3
          const totalDelay = delay + jitter

          console.log(
            `[useVerdict] Reconnecting in ${Math.round(totalDelay)}ms (attempt ${attempt + 1}/${MAX_RECONNECT_ATTEMPTS})`
          )

          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connectWebSocket(sid)
          }, totalDelay)
        } else {
          console.error('[useVerdict] Max reconnection attempts reached')
          setError('Connection lost. Please refresh to try again.')
        }
      }
    },
    [handleEvent, setError]
  )

  /**
   * Submit a new decision for adversarial evaluation.
   * Creates a REST session, then opens a WebSocket for streaming.
   * @param {string} question - The decision to evaluate
   * @param {string} [context] - Additional context
   * @param {string} [format='executive'] - Output format
   */
  const submit = useCallback(
    async (question, context, format = 'executive') => {
      try {
        // Create session via REST
        const res = await fetch(`${API_BASE}/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, context, output_format: format }),
        })

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(errorData.detail || `Failed to create session: ${res.statusText}`)
        }

        const data = await res.json()
        const session_id = data.session_id
        const sessionDecision = data.decision
        console.log('[useVerdict] Session created:', session_id)
        startSession(session_id, sessionDecision)

        // Store session ID for reconnection
        sessionIdRef.current = session_id
        reconnectAttemptsRef.current = 0

        // Connect WebSocket with reconnection support
        connectWebSocket(session_id)
      } catch (err) {
        console.error('[useVerdict] Submit failed:', err)
        setError(err.message)
      }
    },
    [startSession, connectWebSocket, setError]
  )

  /**
   * Disconnect the WebSocket and clean up reconnection timers.
   */
  const disconnect = useCallback(() => {
    sessionIdRef.current = null
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected')
      wsRef.current = null
    }
  }, [])

  return {
    submit,
    disconnect,
    screen,
    sessionId,
    decision,
    agentStates,
    feed,
    verdict,
    synthesis,
    error,
    startTime,
  }
}
