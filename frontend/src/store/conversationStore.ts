// Conversation store: persists all chat history to the browser's localStorage.
// Survives page refresh. Supports auto-naming from the first user message and
// deleting conversations.
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ChatMessage, Conversation } from '../types'
import { uid } from '../utils/id'

interface ConversationState {
  conversations: Conversation[]
  activeId: string | null

  createConversation: () => string
  deleteConversation: (id: string) => void
  setActive: (id: string | null) => void
  getActive: () => Conversation | null

  addMessage: (conversationId: string, message: ChatMessage) => void
  updateMessage: (conversationId: string, messageId: string, patch: Partial<ChatMessage>) => void
  setSandboxId: (conversationId: string, sandboxId: string) => void
  renameFromFirstMessage: (conversationId: string, firstUserText: string) => void
}

function deriveTitle(text: string): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  if (!clean) return 'New Chat'
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeId: null,

      createConversation: () => {
        const id = uid('conv')
        const now = Date.now()
        const conv: Conversation = {
          id,
          title: 'New Chat',
          messages: [],
          sandboxId: null,
          createdAt: now,
          updatedAt: now,
        }
        set((s) => ({ conversations: [conv, ...s.conversations], activeId: id }))
        return id
      },

      deleteConversation: (id) =>
        set((s) => {
          const conversations = s.conversations.filter((c) => c.id !== id)
          const activeId =
            s.activeId === id ? conversations[0]?.id ?? null : s.activeId
          return { conversations, activeId }
        }),

      setActive: (id) => set({ activeId: id }),

      getActive: () => {
        const s = get()
        return s.conversations.find((c) => c.id === s.activeId) ?? null
      },

      addMessage: (conversationId, message) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messages: [...c.messages, message], updatedAt: Date.now() }
              : c,
          ),
        })),

      updateMessage: (conversationId, messageId, patch) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  updatedAt: Date.now(),
                  messages: c.messages.map((m) =>
                    m.id === messageId ? { ...m, ...patch } : m,
                  ),
                }
              : c,
          ),
        })),

      setSandboxId: (conversationId, sandboxId) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId ? { ...c, sandboxId } : c,
          ),
        })),

      renameFromFirstMessage: (conversationId, firstUserText) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId && (c.title === 'New Chat' || !c.title)
              ? { ...c, title: deriveTitle(firstUserText) }
              : c,
          ),
        })),
    }),
    {
      name: 'vibe-coder-conversations',
    },
  ),
)
