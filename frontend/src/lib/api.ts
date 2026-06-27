// API client: model listing, single-file read, sandbox file tree, kill, and the
// streaming chat endpoint with a robust token-by-token SSE reader.

import { API } from './config'
import type { AgentEvent, FileNode, ModelInfo, Provider } from '../types'

export interface StreamPayload {
  credentials: {
    provider: Provider
    api_key: string
    model: string
    e2b_api_key: string
    sandbox_template?: string | null
  }
  history: Array<{
    role: 'user' | 'assistant' | 'tool' | 'system'
    content?: string | null
    tool_calls?: unknown
    tool_call_id?: string
  }>
  message: string
  sandbox_id?: string | null
}

export async function fetchModels(provider: Provider, apiKey: string): Promise<ModelInfo[]> {
  const resp = await fetch(API.models, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, api_key: apiKey }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to fetch models (${resp.status})`)
  }
  const data = await resp.json()
  return data.models as ModelInfo[]
}

export async function fetchFileTree(
  sandboxId: string,
  e2bApiKey: string,
): Promise<FileNode[]> {
  const resp = await fetch(API.sandboxFiles, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sandbox_id: sandboxId, e2b_api_key: e2bApiKey }),
  })
  if (!resp.ok) return []
  const data = await resp.json()
  return (data.files || []) as FileNode[]
}

export async function readFile(
  sandboxId: string,
  e2bApiKey: string,
  filePath: string,
): Promise<string> {
  const resp = await fetch(API.sandboxFile, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sandbox_id: sandboxId, e2b_api_key: e2bApiKey, file_path: filePath }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to read file (${resp.status})`)
  }
  const data = await resp.json()
  return data.content as string
}

/**
 * Stream a chat turn. Parses the SSE byte stream incrementally and invokes
 * `onEvent` for each structured agent event as soon as it arrives, enabling
 * smooth token-by-token rendering. Supports cancellation via AbortSignal.
 */
export async function streamChat(
  payload: StreamPayload,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(API.chatStream, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!resp.ok || !resp.body) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `Stream failed (${resp.status})`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Read until the stream closes, parsing complete SSE frames (separated by
  // a blank line). Partial frames remain buffered until completed.
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sepIndex: number
    // Frames are delimited by a blank line ("\n\n").
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sepIndex)
      buffer = buffer.slice(sepIndex + 2)

      const dataLines = frame
        .split('\n')
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trim())

      if (dataLines.length === 0) continue // comment/heartbeat frame
      const raw = dataLines.join('\n')
      try {
        const evt = JSON.parse(raw) as AgentEvent
        onEvent(evt)
      } catch {
        // Ignore malformed fragments; the next frame will be well-formed.
      }
    }
  }
}
