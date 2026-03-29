/**
 * verdictStore — Zustand state management for the Verdict courtroom.
 *
 * Manages the complete application state including:
 * - Screen navigation (landing vs courtroom)
 * - Session metadata (ID, decision, timing)
 * - Agent states (status, thinking text, output) for all 6+ agents
 * - Feed of real-time events from the WebSocket stream
 * - Final verdict and synthesis results
 * - Error state for user feedback
 *
 * Agent state machine: waiting → active → complete
 * Witnesses are stored as an array since they're dynamically spawned.
 *
 * @module verdictStore
 */

import { create } from 'zustand'

/** @type {Object} Default agent states before session starts */
const initialAgentStates = {
  research: { status: 'waiting', thinking: '', output: null },
  prosecutor: { status: 'waiting', thinking: '', output: null },
  defense: { status: 'waiting', thinking: '', output: null },
  judge: { status: 'waiting', thinking: '', output: null },
  witnesses: [],
  synthesis: { status: 'waiting', thinking: '', output: null },
}

/**
 * Zustand store for verdict session state.
 *
 * @typedef {Object} VerdictState
 * @property {string} screen - Current screen ('landing' | 'courtroom')
 * @property {string|null} sessionId - Active session UUID
 * @property {Object|null} decision - User's decision input
 * @property {Object} agentStates - Per-agent status, thinking text, and output
 * @property {Array} feed - Ordered list of WebSocket events
 * @property {Object|null} verdict - Judge's final verdict
 * @property {Object|null} synthesis - Battle-tested synthesis output
 * @property {string|null} error - Current error message for user feedback
 * @property {number|null} startTime - Session start timestamp (ms)
 */
const useVerdictStore = create((set, get) => ({
  screen: 'landing',
  sessionId: null,
  decision: null,
  agentStates: { ...initialAgentStates },
  feed: [],
  verdict: null,
  synthesis: null,
  error: null,
  startTime: null,

  /** Navigate to a specific screen */
  setScreen: (screen) => set({ screen }),

  /**
   * Initialize a new session — resets all agent states and transitions to courtroom.
   * @param {string} sessionId - The new session UUID
   * @param {Object} decision - The user's decision input
   */
  startSession: (sessionId, decision) =>
    set({
      sessionId,
      decision,
      screen: 'courtroom',
      agentStates: { ...initialAgentStates },
      feed: [],
      verdict: null,
      synthesis: null,
      error: null,
      startTime: Date.now(),
    }),

  /**
   * Update a specific agent's state (status, thinking text, or output).
   * Handles witness agents specially since they're stored as an array.
   * @param {string} agentName - Agent identifier (e.g., 'research', 'witness_fact')
   * @param {Object} updates - Partial state updates to merge
   */
  updateAgent: (agentName, updates) =>
    set((state) => {
      if (agentName.startsWith('witness_')) {
        const witnesses = [...state.agentStates.witnesses]
        const existingIdx = witnesses.findIndex((w) => w.type === agentName)
        if (existingIdx >= 0) {
          witnesses[existingIdx] = { ...witnesses[existingIdx], ...updates }
        } else {
          witnesses.push({ type: agentName, status: 'active', thinking: '', output: null, ...updates })
        }
        return {
          agentStates: { ...state.agentStates, witnesses },
        }
      }
      return {
        agentStates: {
          ...state.agentStates,
          [agentName]: { ...state.agentStates[agentName], ...updates },
        },
      }
    }),

  /**
   * Append a new event to the real-time feed.
   * @param {Object} item - StreamEvent data from WebSocket
   */
  addFeedItem: (item) =>
    set((state) => ({
      feed: [...state.feed, { ...item, id: state.feed.length, receivedAt: Date.now() }],
    })),

  /** Set the final verdict result from the Judge agent */
  setVerdict: (verdict) => set({ verdict }),

  /** Set the battle-tested synthesis output */
  setSynthesis: (synthesis) => set({ synthesis }),

  /** Set error message for user feedback */
  setError: (error) => set({ error }),

  /** Reset all state and return to landing screen */
  reset: () =>
    set({
      screen: 'landing',
      sessionId: null,
      decision: null,
      agentStates: { ...initialAgentStates },
      feed: [],
      verdict: null,
      synthesis: null,
      error: null,
      startTime: null,
    }),
}))

// Expose store for debugging in development
if (typeof window !== 'undefined') {
  window.__verdictStore = useVerdictStore
}

export default useVerdictStore
