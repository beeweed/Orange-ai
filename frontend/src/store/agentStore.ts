// Live agent run store: transient UI state during an active streaming turn.
// Tracks streaming status, current iteration, sandbox creation phase, the live
// streaming text, in-flight tool activities, the sandbox file tree, and the
// explicit sandbox lifecycle state for pause/resume controls.
import { create } from 'zustand'
import type { FileNode } from '../types'

export type AgentPhase = 'idle' | 'creating_sandbox' | 'thinking' | 'streaming' | 'tool'
export type SandboxStatusState = 'none' | 'running' | 'paused' | 'error'

interface AgentState {
  phase: AgentPhase
  isRunning: boolean
  iteration: number
  maxIteration: number
  sandboxId: string | null
  sandboxState: SandboxStatusState
  sandboxBusy: boolean
  sandboxExpiresAt: string | null
  sandboxStatusError: string | null
  fileTree: FileNode[]
  error: string | null

  setPhase: (p: AgentPhase) => void
  setRunning: (b: boolean) => void
  setIteration: (current: number, max: number) => void
  resetIteration: () => void
  setSandboxId: (id: string | null) => void
  setSandboxStatus: (state: SandboxStatusState, expiresAt?: string | null) => void
  setSandboxBusy: (busy: boolean) => void
  setSandboxStatusError: (error: string | null) => void
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
  sandboxState: 'none',
  sandboxBusy: false,
  sandboxExpiresAt: null,
  sandboxStatusError: null,
  fileTree: [],
  error: null,

  setPhase: (phase) => set({ phase }),
  setRunning: (isRunning) => set({ isRunning }),
  setIteration: (iteration, maxIteration) => set({ iteration, maxIteration }),
  resetIteration: () => set({ iteration: 0 }),
  setSandboxId: (sandboxId) =>
    set((state) => ({
      sandboxId,
      sandboxState: sandboxId ? state.sandboxState : 'none',
      sandboxExpiresAt: sandboxId ? state.sandboxExpiresAt : null,
      sandboxStatusError: sandboxId ? state.sandboxStatusError : null,
    })),
  setSandboxStatus: (sandboxState, sandboxExpiresAt = null) => set({ sandboxState, sandboxExpiresAt }),
  setSandboxBusy: (sandboxBusy) => set({ sandboxBusy }),
  setSandboxStatusError: (sandboxStatusError) => set({ sandboxStatusError }),
  setFileTree: (fileTree) => set({ fileTree }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      phase: 'idle',
      isRunning: false,
      iteration: 0,
      sandboxId: null,
      sandboxState: 'none',
      sandboxBusy: false,
      sandboxExpiresAt: null,
      sandboxStatusError: null,
      fileTree: [],
      error: null,
    }),
}))