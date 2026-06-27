// Left-side chat panel: header (menu, logo, iteration, settings), message list
// with streaming + thinking/sandbox indicators, and the input box.
import { useEffect, useRef } from 'react'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { useSettingsStore } from '../store/settingsStore'
import { useAgentRun } from '../hooks/useAgentRun'
import { AssistantMessage, UserMessage } from './Message'
import { ChatInput } from './ChatInput'
import { ThinkingIndicator } from './ThinkingIndicator'
import { MenuIcon, SettingsIcon, SparkIcon } from './Icons'

interface Props {
  onOpenSettings: () => void
  onOpenHistory: () => void
  onOpenFile: (path: string) => void
}

export function ChatPanel({ onOpenSettings, onOpenHistory, onOpenFile }: Props) {
  const active = useConversationStore((s) =>
    s.conversations.find((c) => c.id === s.activeId) ?? null,
  )
  const agent = useAgentStore()
  const settings = useSettingsStore()
  const { send } = useAgentRun()
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages = active?.messages ?? []
  const configured = settings.isConfigured()

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, agent.phase, agent.iteration])

  // Determine whether to show a standalone indicator (no assistant content yet).
  const lastMsg = messages[messages.length - 1]
  const assistantStreaming =
    agent.isRunning && lastMsg?.role === 'assistant' && Boolean(lastMsg.content)
  const showSandboxIndicator = agent.isRunning && agent.phase === 'creating_sandbox'
  const showThinkingIndicator =
    agent.isRunning &&
    !showSandboxIndicator &&
    (agent.phase === 'thinking' || agent.phase === 'tool') &&
    (!lastMsg || lastMsg.role !== 'assistant' || !lastMsg.content)

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#1e1e1e]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-5 py-4 bg-[#252525] border-b border-border/30">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onOpenHistory}
            className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all"
            title="Chat history"
          >
            <MenuIcon className="w-5 h-5" />
          </button>
          <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center shadow-lg shadow-primary/20 shrink-0">
            <SparkIcon className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">Vibe Coder</h1>
            <p className="text-[11px] text-muted-foreground">Autonomous AI Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Iteration counter (top of the application) */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-[10px] font-medium text-primary whitespace-nowrap">
              Iter {agent.iteration}/{agent.maxIteration}
            </span>
          </div>
          <button
            onClick={onOpenSettings}
            className="p-2.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all"
            title="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Mobile iteration bar */}
      <div className="sm:hidden flex items-center justify-center px-4 py-1.5 bg-[#1e1e1e] border-b border-border/20">
        <div className="inline-flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          <span className="text-[10px] font-medium text-primary">
            Iteration {agent.iteration}/{agent.maxIteration}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {messages.length === 0 && !agent.isRunning && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mb-4">
              <SparkIcon className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-foreground mb-1">
              Build anything, autonomously
            </h2>
            <p className="text-sm text-muted-foreground max-w-sm">
              {configured
                ? 'Describe what you want to build. The agent will create files in a live E2B sandbox.'
                : 'Open Settings to add your provider API key, select a model, and add your E2B sandbox key.'}
            </p>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === 'user' ? (
            <UserMessage key={m.id} message={m} />
          ) : (
            <AssistantMessage
              key={m.id}
              message={m}
              streaming={agent.isRunning && i === messages.length - 1 && assistantStreaming}
              onOpenFile={onOpenFile}
            />
          ),
        )}

        {showSandboxIndicator && (
          <ThinkingIndicator label="creating sandbox..." variant="shimmer" />
        )}
        {showThinkingIndicator && <ThinkingIndicator label="thinking..." />}
      </div>

      {/* Input */}
      <ChatInput
        onSend={send}
        running={agent.isRunning}
        disabled={!configured}
        placeholder={
          configured
            ? 'Describe what you want to build...'
            : 'Configure settings first (API key, model, E2B key)...'
        }
      />
    </div>
  )
}
