// Chat history sidebar (slide-in). Lists all persisted conversations from
// localStorage, supports selecting, creating, and deleting conversations.
import { useConversationStore } from '../store/conversationStore'
import { useAgentStore } from '../store/agentStore'
import { cn } from '../utils/cn'
import { ChatBubbleIcon, CloseIcon, PlusIcon, TrashIcon } from './Icons'

interface Props {
  open: boolean
  onClose: () => void
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

export function HistorySidebar({ open, onClose }: Props) {
  const { conversations, activeId, setActive, createConversation, deleteConversation } =
    useConversationStore()
  const agent = useAgentStore()

  const select = (id: string) => {
    if (agent.isRunning) return
    setActive(id)
    const conv = conversations.find((c) => c.id === id)
    agent.setSandboxId(conv?.sandboxId ?? null)
    agent.setFileTree([])
    onClose()
  }

  const newChat = () => {
    if (agent.isRunning) return
    createConversation()
    agent.reset()
    agent.setSandboxId(null)
    agent.setFileTree([])
    onClose()
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={onClose}
      />
      {/* Panel */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 h-full w-[85vw] max-w-[340px] bg-[#1c1c1c] border-r border-border/30 shadow-2xl flex flex-col transition-transform duration-300',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-border/30">
          <div className="flex items-center gap-2">
            <ChatBubbleIcon className="w-5 h-5 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Chat History</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
          >
            <CloseIcon className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3">
          <button
            onClick={newChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-primary/15 border border-primary/30 text-sm font-medium text-primary hover:bg-primary/20 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-muted-foreground text-center px-4 py-8">
              No conversations yet. Start a new chat.
            </p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => select(c.id)}
              className={cn(
                'group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-colors',
                c.id === activeId ? 'bg-primary/15 border border-primary/25' : 'hover:bg-white/5 border border-transparent',
              )}
            >
              <ChatBubbleIcon className="w-4 h-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">{c.title}</p>
                <p className="text-[10px] text-muted-foreground">
                  {c.messages.length} msgs · {timeAgo(c.updatedAt)}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  deleteConversation(c.id)
                }}
                className="p-1.5 rounded-md text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive hover:bg-destructive/10 transition-all"
                title="Delete chat"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </aside>
    </>
  )
}
