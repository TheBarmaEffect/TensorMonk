import { useCallback, useRef } from 'react'
import useVerdictStore from '../store/verdictStore'

const API_BASE = '/api/verdict'

function getWsUrl(sessionId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${API_BASE}/${sessionId}/stream`
}

export default function useVerdict() {
  const wsRef = useRef(null)
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
          break
        default:
          break
      }
    },
    [updateAgent, addFeedItem, setVerdict, setSynthesis, setError]
  )

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
          throw new Error(`Failed to create session: ${res.statusText}`)
        }

        const { session_id, decision } = await res.json()
        startSession(session_id, decision)

        // Connect WebSocket
        const ws = new WebSocket(getWsUrl(session_id))
        wsRef.current = ws

        ws.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data)
            handleEvent(event)
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err)
          }
        }

        ws.onerror = (e) => {
          console.error('WebSocket error:', e)
          setError('Connection error. Please try again.')
        }

        ws.onclose = () => {
          console.log('WebSocket closed')
        }
      } catch (err) {
        console.error('Submit failed:', err)
        setError(err.message)
      }
    },
    [startSession, handleEvent, setError]
  )

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
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
