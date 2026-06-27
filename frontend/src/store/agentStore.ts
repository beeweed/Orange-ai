// Live agent run store: transient UI state during an active streaming turn.
// Tracks streaming status, current iteration, sandbox creation phase, the live
// streaming text, in-flight tool activities, and the sandbox file tree.
import { create } from 'zustand'
import type { FileNode } from '../types'

export type AgentPhase = 'idle' | 'creating_sandbox' | 'thinking' | 'streaming' | 'tool'

interface AgentState {
  phase: AgentPhase
  isRunning: boolean
  iteration: number
  maxIteration: number
  sandboxId: string | null
  fileTree: FileNode[]
  error: string | null

  setPhase: (p: AgentPhase) => void
  setRunning: (b: boolean) => void
  setIteration: (current: number, max: number) => void
  resetIteration: () => void
  setSandboxId: (id: string | null) => void
  setFileTree: (files: FileNode[]) => void
  setError: (e: string | null) => void
  reset: () => void
}

export const useAgentStore = create<AgentState>((set) => ({
  phase: 'idle',
  isRunning: false,
  iteration: 0,
  maxIteration: 1000,
  sandboxId: null,
  fileTree: [],
  error: null,

  setPhase: (phase) => set({ phase }),
  setRunning: (isRunning) => set({ isRunning }),
  setIteration: (iteration, maxIteration) => set({ iteration, maxIteration }),
  resetIteration: () => set({ iteration: 0 }),
  setSandboxId: (sandboxId) => set({ sandboxId }),
  setFileTree: (fileTree) => set({ fileTree }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      phase: 'idle',
      isRunning: false,
      iteration: 0,
      error: null,
    }),
}))
