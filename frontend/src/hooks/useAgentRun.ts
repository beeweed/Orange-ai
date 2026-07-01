// useAgentRun: orchestrates a single agent turn end-to-end.
// - Builds provider-shaped history from the persisted conversation.
// - Opens the SSE stream and applies each event to the live + persisted stores.
// - Handles sandbox creation phase, token streaming, tool chips, iteration,
//   file-tree updates, errors, and completion.
import { useCallback, useRef } from 'react'
import { streamChat, type StreamPayload } from '../lib/api'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { useSettingsStore } from '../store/settingsStore'
import type { ChatMessage, ToolActivity } from '../types'
import { uid } from '../utils/id'

export function useAgentRun() {
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(async (userText: string) => {
    const settings = useSettingsStore.getState()
    const convStore = useConversationStore.getState()
    const agent = useAgentStore.getState()

    if (agent.isRunning) return
    const text = userText.trim()
    if (!text) return

    // Ensure there is an active conversation.
    let conversationId = convStore.activeId
    if (!conversationId) {
      conversationId = convStore.createConversation()
    }
    const cid = conversationId

    // Capture conversation state BEFORE adding the user message.
    const convBefore = useConversationStore
      .getState()
      .conversations.find((c) => c.id === cid)
    const isFirst = !convBefore || convBefore.messages.length === 0

    // Persist the user message and auto-name the chat from the first message.
    const userMsg: ChatMessage = {
      id: uid('msg'),
      role: 'user',
      content: text,
      createdAt: Date.now(),
    }
    convStore.addMessage(cid, userMsg)
    if (isFirst) convStore.renameFromFirstMessage(cid, text)

    // Build provider history from prior messages (exclude the just-added one).
    const priorMessages = (convBefore?.messages ?? []).filter(
      (m) => m.role === 'user' || m.role === 'assistant',
    )
    const history = priorMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    // Reset iteration on every user message (as required).
    agent.resetIteration()
    agent.setError(null)
    agent.setRunning(true)
    agent.setPhase('thinking')

    // Create the placeholder assistant message we stream into.
    const assistantId = uid('msg')
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      tools: [],
      iteration: 0,
      createdAt: Date.now(),
    }
    convStore.addMessage(cid, assistantMsg)

    // Local mutable buffers (avoid excessive store churn per token).
    let liveContent = ''
    const tools: ToolActivity[] = []
    let lastFlush = 0

    const flush = (force = false) => {
      const now = performance.now()
      if (!force && now - lastFlush < 24) return
      lastFlush = now
      useConversationStore.getState().updateMessage(cid, assistantId, {
        content: liveContent,
        tools: [...tools],
        iteration: useAgentStore.getState().iteration,
      })
    }

    const existingSandbox =
      convBefore?.sandboxId ?? useAgentStore.getState().sandboxId ?? null

    const payload: StreamPayload = {
      credentials: {
        provider: settings.provider,
        api_key: settings.activeApiKey(),
        model: settings.model,
        e2b_api_key: settings.e2bApiKey,
        sandbox_template: settings.sandboxTemplate || null,
      },
      history,
      message: text,
      sandbox_id: existingSandbox,
    }

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamChat(
        payload,
        (evt) => {
          const a = useAgentStore.getState()
          switch (evt.type) {
            case 'sandbox_creating':
              a.setPhase('creating_sandbox')
              break
            case 'sandbox_created':
            case 'sandbox_ready':
              a.setSandboxId(evt.sandbox_id)
              a.setSandboxStatus('running')
              a.setSandboxStatusError(null)
              useConversationStore.getState().setSandboxId(cid, evt.sandbox_id)
              a.setPhase('thinking')
              break
            case 'iteration':
              a.setIteration(evt.current, evt.max)
              break
            case 'thinking':
              if (a.phase !== 'creating_sandbox') a.setPhase('thinking')
              break
            case 'content_start':
              a.setPhase('streaming')
              break
            case 'token':
              liveContent += evt.text
              flush()
              break
            case 'tool_call': {
              a.setPhase('tool')
              const filePath =
                (evt.arguments?.file_path as string | undefined) ?? undefined
              tools.push({
                id: evt.id,
                name: evt.name,
                display: evt.display,
                filePath,
                arguments: evt.arguments,
                status: 'running',
              })
              flush(true)
              break
            }
            case 'tool_result': {
              const t = tools.find((x) => x.id === evt.id)
              if (t) {
                t.status = evt.ok ? 'success' : 'error'
                t.result = evt.result
              }
              a.setPhase('thinking')
              flush(true)
              break
            }
            case 'message_done':
              flush(true)
              break
            case 'file_tree':
              a.setFileTree(evt.files)
              break
            case 'error':
              a.setError(evt.message)
              if (evt.message.toLowerCase().includes('sandbox is paused')) {
                a.setSandboxStatus('paused')
              }
              liveContent += liveContent
                ? `\n\n> Error: ${evt.message}`
                : `> Error: ${evt.message}`
              flush(true)
              break
            case 'done':
              flush(true)
              break
          }
        },
        controller.signal,
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown streaming error'
      const liveAgent = useAgentStore.getState()
      liveAgent.setError(message)
      if (message.toLowerCase().includes('sandbox is paused')) {
        liveAgent.setSandboxStatus('paused')
      }
      liveContent += liveContent ? `\n\n> Error: ${message}` : `> Error: ${message}`
      flush(true)
    } finally {
      flush(true)
      const a = useAgentStore.getState()
      a.setRunning(false)
      a.setPhase('idle')
      abortRef.current = null
    }
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    const a = useAgentStore.getState()
    a.setRunning(false)
    a.setPhase('idle')
  }, [])

  return { send, stop }
}
