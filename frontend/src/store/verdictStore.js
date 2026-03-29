import { create } from 'zustand'

const initialAgentStates = {
  research: { status: 'waiting', thinking: '', output: null },
  prosecutor: { status: 'waiting', thinking: '', output: null },
  defense: { status: 'waiting', thinking: '', output: null },
  judge: { status: 'waiting', thinking: '', output: null },
  witnesses: [],
  synthesis: { status: 'waiting', thinking: '', output: null },
}

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

  setScreen: (screen) => set({ screen }),

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

  addFeedItem: (item) =>
    set((state) => ({
      feed: [...state.feed, { ...item, id: state.feed.length, receivedAt: Date.now() }],
    })),

  setVerdict: (verdict) => set({ verdict }),
  setSynthesis: (synthesis) => set({ synthesis }),
  setError: (error) => set({ error }),

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

// Expose store for debugging
if (typeof window !== 'undefined') {
  window.__verdictStore = useVerdictStore
}

export default useVerdictStore
