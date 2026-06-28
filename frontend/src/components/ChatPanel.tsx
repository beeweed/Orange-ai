// Left-side chat panel: header (menu, logo, iteration, sandbox controls,
// settings), message list with streaming + thinking/sandbox indicators, and the
// input box.
import { useEffect, useRef } from 'react'
import { fetchSandboxStatus, pauseSandbox, resumeSandbox } from '../lib/api'
import { useAgentStore } from '../store/agentStore'
import { useConversationStore } from '../store/conversationStore'
import { useSettingsStore } from '../store/settingsStore'
import { useAgentRun } from '../hooks/useAgentRun'
import { AssistantMessage, UserMessage } from './Message'
import { ChatInput } from './ChatInput'
import { ThinkingIndicator } from './ThinkingIndicator'
import { MenuIcon, PauseIcon, PlayIcon, RefreshIcon, SettingsIcon, SparkIcon } from './Icons'

interface Props {
  onOpenSettings: () => void
  onOpenHistory: () => void
  onOpenFile: (path: string) => void
}

function formatSandboxWindow(expiresAt: string | null): string {
  if (!expiresAt) return '1h window active'
  const ms = new Date(expiresAt).getTime() - Date.now()
  if (Number.isNaN(ms) || ms <= 0) return 'timeout reached'
  const totalMinutes = Math.ceil(ms / 60000)
  if (totalMinutes >= 60) return `${Math.ceil(totalMinutes / 60)}h remaining`
  return `${totalMinutes}m remaining`
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
  const sandboxId = active?.sandboxId ?? agent.sandboxId
  const sandboxPaused = agent.sandboxState === 'paused'
  const sandboxRunning = agent.sandboxState === 'running'
  const controlDisabled = !sandboxId || !settings.e2bApiKey || agent.isRunning || agent.sandboxBusy

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, agent.phase, agent.iteration])

  useEffect(() => {
    let cancelled = false

    const syncSandboxState = async () => {
      if (!sandboxId) {
        agent.setSandboxStatus('none')
        agent.setSandboxStatusError(null)
        agent.setSandboxBusy(false)
        return
      }
      if (!settings.e2bApiKey) return

      agent.setSandboxBusy(true)
      agent.setSandboxStatusError(null)
      try {
        const status = await fetchSandboxStatus(sandboxId, settings.e2bApiKey)
        if (cancelled) return
        agent.setSandboxId(status.sandbox_id)
        agent.setSandboxStatus(status.state, status.end_at)
      } catch (err) {
        if (cancelled) return
        agent.setSandboxStatus('error')
        agent.setSandboxStatusError(
          err instanceof Error ? err.message : 'Failed to inspect sandbox state',
        )
      } finally {
        if (!cancelled) agent.setSandboxBusy(false)
      }
    }

    void syncSandboxState()

    return () => {
      cancelled = true
    }
  }, [sandboxId, settings.e2bApiKey])

  const toggleSandbox = async () => {
    if (!sandboxId || !settings.e2bApiKey || controlDisabled) return

    agent.setSandboxBusy(true)
    agent.setSandboxStatusError(null)

    try {
      const next = sandboxPaused
        ? await resumeSandbox(sandboxId, settings.e2bApiKey)
        : await pauseSandbox(sandboxId, settings.e2bApiKey)
      agent.setSandboxStatus(next.state, next.end_at)
    } catch (err) {
      agent.setSandboxStatusError(
        err instanceof Error ? err.message : `Failed to ${sandboxPaused ? 'resume' : 'pause'} sandbox`,
      )
    } finally {
      agent.setSandboxBusy(false)
    }
  }

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

  const sandboxLabel = !sandboxId
    ? 'No sandbox'
    : agent.sandboxBusy
      ? 'Syncing sandbox…'
      : sandboxPaused
        ? 'Sandbox paused'
        : sandboxRunning
          ? formatSandboxWindow(agent.sandboxExpiresAt)
          : 'Sandbox unavailable'

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#1e1e1e]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-5 py-4 bg-[#252525] border-b border-border/30 gap-3">
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
        <div className="flex items-center gap-2 shrink-0">
          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 min-w-0">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                sandboxPaused
                  ? 'bg-amber-400'
                  : sandboxRunning
                    ? 'bg-emerald-400 animate-pulse'
                    : 'bg-muted-foreground/60'
              }`}
            />
            <span className="text-[10px] font-medium text-foreground whitespace-nowrap">
              {sandboxLabel}
            </span>
          </div>
          {/* Iteration counter (top of the application) */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-[10px] font-medium text-primary whitespace-nowrap">
              Iter {agent.iteration}/{agent.maxIteration}
            </span>
          </div>
          <button
            onClick={toggleSandbox}
            disabled={controlDisabled}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-medium transition-all ${
              controlDisabled
                ? 'border-white/10 bg-white/5 text-muted-foreground cursor-not-allowed'
                : sandboxPaused
                  ? 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300 hover:bg-emerald-500/18'
                  : 'border-amber-500/30 bg-amber-500/12 text-amber-200 hover:bg-amber-500/18'
            }`}
            title={sandboxPaused ? 'Resume sandbox' : 'Pause sandbox'}
          >
            {agent.sandboxBusy ? (
              <RefreshIcon className="w-3.5 h-3.5 animate-spin" />
            ) : sandboxPaused ? (
              <PlayIcon className="w-3.5 h-3.5" />
            ) : (
              <PauseIcon className="w-3.5 h-3.5" />
            )}
            <span className="hidden sm:inline">{sandboxPaused ? 'Resume' : 'Pause'}</span>
          </button>
          <button
            onClick={onOpenSettings}
            className="p-2.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all"
            title="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Mobile status bars */}
      <div className="sm:hidden flex items-center justify-between px-4 py-1.5 bg-[#1e1e1e] border-b border-border/20 gap-3">
        <span className="text-[10px] font-medium text-muted-foreground truncate">{sandboxLabel}</span>
        <div className="inline-flex items-center gap-1.5 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          <span className="text-[10px] font-medium text-primary">
            Iteration {agent.iteration}/{agent.maxIteration}
          </span>
        </div>
      </div>

      {agent.sandboxStatusError && (
        <div className="px-4 sm:px-5 py-2 border-b border-destructive/20 bg-destructive/10 text-[11px] text-destructive">
          {agent.sandboxStatusError}
        </div>
      )}

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
        disabled={!configured || sandboxPaused}
        placeholder={
          !configured
            ? 'Configure settings first (API key, model, E2B key)...'
            : sandboxPaused
              ? 'Resume the sandbox to continue working...'
              : 'Describe what you want to build...'
        }
      />
    </div>
  )
}