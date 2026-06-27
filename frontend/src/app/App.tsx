// Root application shell.
// - Desktop: chat panel (left) + code panel (right).
// - Mobile: tab-switched single panel (Chat | Files).
// Manages global dialogs (settings), the history sidebar, and cross-panel
// "open file" requests.
import { useEffect, useState } from 'react'
import { ChatPanel } from '../components/ChatPanel'
import { CodePanel } from '../components/CodePanel'
import { HistorySidebar } from '../components/HistorySidebar'
import { SettingsDialog } from '../components/SettingsDialog'
import { ChatBubbleIcon, FolderTreeIcon } from '../components/Icons'
import { useConversationStore } from '../store/conversationStore'
import { useSettingsStore } from '../store/settingsStore'
import { cn } from '../utils/cn'

type MobileTab = 'chat' | 'files'

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [mobileTab, setMobileTab] = useState<MobileTab>('chat')
  const [requestedFile, setRequestedFile] = useState<string | null>(null)

  const { conversations, activeId, createConversation, setActive } = useConversationStore()
  const isConfigured = useSettingsStore((s) => s.isConfigured())

  // Ensure there's always an active conversation.
  useEffect(() => {
    if (!activeId) {
      if (conversations.length > 0) setActive(conversations[0].id)
      else createConversation()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Open settings automatically on first run if nothing is configured.
  useEffect(() => {
    if (!isConfigured) setSettingsOpen(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const openFile = (path: string) => {
    setRequestedFile(path)
    setMobileTab('files')
  }

  return (
    <div className="h-full w-full overflow-hidden bg-[#191919]">
      {/* Desktop layout */}
      <div className="hidden md:flex h-full">
        <div className="w-[420px] min-w-[360px] max-w-[520px] shrink-0 lg:w-[40%] p-3">
          <div className="h-full rounded-3xl border border-white/5 overflow-hidden">
            <ChatPanel
              onOpenSettings={() => setSettingsOpen(true)}
              onOpenHistory={() => setHistoryOpen(true)}
              onOpenFile={openFile}
            />
          </div>
        </div>
        <div className="flex-1 min-w-0 flex h-full">
          <CodePanel
            requestedPath={requestedFile}
            onConsumeRequest={() => setRequestedFile(null)}
          />
        </div>
      </div>

      {/* Mobile layout */}
      <div className="md:hidden flex flex-col h-full">
        <div className="flex-1 min-h-0">
          <div className={cn('h-full', mobileTab === 'chat' ? 'block' : 'hidden')}>
            <ChatPanel
              onOpenSettings={() => setSettingsOpen(true)}
              onOpenHistory={() => setHistoryOpen(true)}
              onOpenFile={openFile}
            />
          </div>
          <div className={cn('h-full', mobileTab === 'files' ? 'block' : 'hidden')}>
            <CodePanel
              requestedPath={requestedFile}
              onConsumeRequest={() => setRequestedFile(null)}
            />
          </div>
        </div>
        {/* Mobile tab bar */}
        <nav className="flex h-14 bg-[#232323] border-t border-border/30 shrink-0">
          <button
            onClick={() => setMobileTab('chat')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 transition-colors',
              mobileTab === 'chat'
                ? 'text-primary bg-primary/10'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <ChatBubbleIcon className="w-5 h-5" />
            <span className="text-sm font-medium">Chat</span>
          </button>
          <button
            onClick={() => setMobileTab('files')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 transition-colors',
              mobileTab === 'files'
                ? 'text-primary bg-primary/10'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <FolderTreeIcon className="w-5 h-5" />
            <span className="text-sm font-medium">Files</span>
          </button>
        </nav>
      </div>

      {/* Global overlays */}
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <HistorySidebar open={historyOpen} onClose={() => setHistoryOpen(false)} />
    </div>
  )
}
