// Shared domain types for the Vibe Coder frontend.

export type Provider = 'openrouter' | 'nvidia'

export type MessageRole = 'user' | 'assistant'

export interface ModelInfo {
  id: string
  name: string
  description?: string | null
  context_length?: number | null
}

// Tool activity attached to an assistant message (rendered as chips/cards).
export interface ToolActivity {
  id: string
  name: 'file_write' | 'file_read' | 'file_editor' | 'insert_after_line' | string
  display: string // e.g. "create: /home/user/App.tsx"
  filePath?: string
  status: 'running' | 'success' | 'error'
  result?: string
}

// One chat message stored in history (persisted to localStorage).
export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  // Assistant-only: tool activities surfaced during the turn.
  tools?: ToolActivity[]
  // Iteration counter snapshot for the assistant turn.
  iteration?: number
  createdAt: number
}

// A persisted conversation.
export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  sandboxId?: string | null
  createdAt: number
  updatedAt: number
}

// File tree node from the sandbox.
export interface FileNode {
  path: string
  type: 'file' | 'directory'
}

// Settings persisted to localStorage.
export interface AppSettings {
  provider: Provider
  openrouterApiKey: string
  nvidiaApiKey: string
  e2bApiKey: string
  sandboxTemplate: string
  model: string
}

// ---- SSE event payloads from the backend agent stream ---- //
export type AgentEvent =
  | { type: 'sandbox_creating' }
  | { type: 'sandbox_created'; sandbox_id: string }
  | { type: 'sandbox_ready'; sandbox_id: string }
  | { type: 'iteration'; current: number; max: number }
  | { type: 'thinking' }
  | { type: 'content_start' }
  | { type: 'token'; text: string }
  | { type: 'tool_call'; id: string; name: string; arguments: Record<string, unknown>; display: string }
  | { type: 'tool_result'; id: string; name: string; ok: boolean; result: string; meta: Record<string, unknown> }
  | { type: 'message_done'; content: string }
  | { type: 'file_tree'; sandbox_id: string; files: FileNode[] }
  | { type: 'error'; message: string }
  | { type: 'done'; iterations: number }
