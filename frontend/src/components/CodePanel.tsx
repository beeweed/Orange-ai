// Right-side VS Code-style panel: file explorer sidebar + code viewer with tabs,
// breadcrumb, and a status bar. Reads file content on demand from the sandbox.
import { useEffect, useState } from 'react'
import { readFile, fetchFileTree } from '../lib/api'
import { useAgentStore } from '../store/agentStore'
import { useSettingsStore } from '../store/settingsStore'
import { FileTree } from './FileTree'
import {
  ChevronRightIcon,
  CloseIcon,
  CodeIcon,
  FileIcon,
  FolderTreeIcon,
  RefreshIcon,
} from './Icons'
import { cn } from '../utils/cn'

interface OpenTab {
  path: string
  content: string
  loading: boolean
  error?: string
}

interface Props {
  // Path requested to open from elsewhere (e.g. a tool chip click).
  requestedPath?: string | null
  onConsumeRequest?: () => void
}

function basename(path: string): string {
  return path.slice(path.lastIndexOf('/') + 1)
}

function langLabel(name: string): string {
  if (/\.tsx?$/.test(name)) return 'TypeScript React'
  if (/\.jsx?$/.test(name)) return 'JavaScript'
  if (/\.py$/.test(name)) return 'Python'
  if (/\.css$/.test(name)) return 'CSS'
  if (/\.json$/.test(name)) return 'JSON'
  if (/\.md$/.test(name)) return 'Markdown'
  if (/\.html?$/.test(name)) return 'HTML'
  return 'Plain Text'
}

export function CodePanel({ requestedPath, onConsumeRequest }: Props) {
  const fileTree = useAgentStore((s) => s.fileTree)
  const sandboxId = useAgentStore((s) => s.sandboxId)
  const sandboxState = useAgentStore((s) => s.sandboxState)
  const setFileTree = useAgentStore((s) => s.setFileTree)
  const e2bApiKey = useSettingsStore((s) => s.e2bApiKey)

  const [tabs, setTabs] = useState<OpenTab[]>([])
  const [activePath, setActivePath] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const sandboxPaused = sandboxState === 'paused'

  const openFile = async (path: string) => {
    setActivePath(path)
    setTabs((prev) => {
      if (prev.some((t) => t.path === path)) return prev
      return [...prev, { path, content: '', loading: true }]
    })

    if (sandboxPaused) {
      setTabs((prev) =>
        prev.map((t) =>
          t.path === path
            ? { ...t, loading: false, error: 'Sandbox is paused. Resume it to read files.' }
            : t,
        ),
      )
      return
    }

    if (!sandboxId || !e2bApiKey) return
    try {
      const content = await readFile(sandboxId, e2bApiKey, path)
      setTabs((prev) =>
        prev.map((t) => (t.path === path ? { ...t, content, loading: false, error: undefined } : t)),
      )
    } catch (err) {
      setTabs((prev) =>
        prev.map((t) =>
          t.path === path
            ? { ...t, loading: false, error: err instanceof Error ? err.message : 'Read failed' }
            : t,
        ),
      )
    }
  }

  // Honour external open requests (e.g. clicking a tool chip).
  useEffect(() => {
    if (requestedPath) {
      void openFile(requestedPath)
      onConsumeRequest?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedPath])

  const closeTab = (path: string) => {
    setTabs((prev) => {
      const next = prev.filter((t) => t.path !== path)
      if (activePath === path) {
        setActivePath(next.length ? next[next.length - 1].path : null)
      }
      return next
    })
  }

  const refreshTree = async () => {
    if (!sandboxId || !e2bApiKey || sandboxPaused) return
    setRefreshing(true)
    try {
      const files = await fetchFileTree(sandboxId, e2bApiKey)
      setFileTree(files)
    } finally {
      setRefreshing(false)
    }
  }

  const activeTab = tabs.find((t) => t.path === activePath)
  const breadcrumb = activePath
    ? activePath.replace('/home/user/', '').split('/')
    : []

  return (
    <div className="flex h-full min-w-0">
      {/* Explorer sidebar */}
      <div className="w-52 lg:w-64 bg-[#232323] border-r border-border/30 flex flex-col shrink-0">
        <div className="flex items-center justify-between px-3 py-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <FolderTreeIcon className="w-4 h-4 text-muted-foreground" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Explorer
            </span>
          </div>
          <button
            onClick={refreshTree}
            disabled={sandboxPaused}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            title={sandboxPaused ? 'Resume the sandbox to refresh files' : 'Refresh files'}
          >
            <RefreshIcon className={cn('w-3.5 h-3.5', refreshing && 'animate-spin')} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <FileTree files={fileTree} selected={activePath} onSelect={openFile} />
        </div>
      </div>

      {/* Editor area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#1e1e1e]">
        {/* Tabs */}
        <div className="flex items-center h-10 bg-[#1e1e1e] border-b border-border/30 px-2 gap-1 overflow-x-auto">
          {tabs.length === 0 && (
            <span className="text-xs text-muted-foreground px-2">No file open</span>
          )}
          {tabs.map((t) => {
            const isActive = t.path === activePath
            return (
              <div
                key={t.path}
                onClick={() => setActivePath(t.path)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-t-lg cursor-pointer transition-colors shrink-0',
                  isActive
                    ? 'bg-background border-t-2 border-t-primary text-foreground'
                    : 'text-muted-foreground hover:bg-white/5',
                )}
              >
                <CodeIcon className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-medium max-w-[140px] truncate">
                  {basename(t.path)}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    closeTab(t.path)
                  }}
                  className="p-0.5 rounded hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <CloseIcon className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>

        {/* Breadcrumb */}
        {activePath && (
          <div className="flex items-center h-7 px-4 bg-[#1e1e1e] border-b border-border/20 overflow-x-auto">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground whitespace-nowrap">
              {breadcrumb.map((seg, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  <span className={i === breadcrumb.length - 1 ? 'text-foreground' : ''}>
                    {seg}
                  </span>
                  {i < breadcrumb.length - 1 && <ChevronRightIcon className="w-3 h-3" />}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Code content */}
        <div className="flex-1 overflow-auto">
          {!activeTab && (
            <div className="h-full flex flex-col items-center justify-center text-center px-8">
              <FileIcon className="w-12 h-12 text-muted-foreground/40 mb-3" />
              <p className="text-sm text-muted-foreground">
                Select a file from the explorer to view its contents.
              </p>
            </div>
          )}
          {activeTab?.loading && (
            <div className="h-full flex items-center justify-center">
              <RefreshIcon className="w-6 h-6 text-primary animate-spin" />
            </div>
          )}
          {activeTab?.error && (
            <div className="p-4">
              <p className="text-sm text-destructive">Error: {activeTab.error}</p>
            </div>
          )}
          {activeTab && !activeTab.loading && !activeTab.error && (
            <pre className="p-4 font-mono text-[13px] leading-6 text-[#abb2bf] whitespace-pre">
              {activeTab.content.split('\n').map((line, i) => (
                <div key={i} className="flex">
                  <span className="select-none text-right pr-4 text-muted-foreground/40 w-12 shrink-0">
                    {i + 1}
                  </span>
                  <span className="flex-1">{line || ' '}</span>
                </div>
              ))}
            </pre>
          )}
        </div>

        {/* Status bar */}
        <div className="flex items-center justify-between h-6 px-3 bg-[#232323] border-t border-border/30 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>{activePath ? langLabel(basename(activePath)) : 'Ready'}</span>
            <span>UTF-8</span>
          </div>
          <div className="flex items-center gap-4">
            <span>
              {sandboxId
                ? `Sandbox: ${sandboxId.slice(0, 10)}…${sandboxPaused ? ' · paused' : ''}`
                : 'No sandbox'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
