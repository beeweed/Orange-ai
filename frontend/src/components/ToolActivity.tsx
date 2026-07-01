// Minimal chip-style tool activity blocks. Rendered inline within an assistant
// message (not in a fixed position). Shows "create: PATH" for file_write and
// "read: PATH" for file_read, with running/success/error states.
import { cn } from '../utils/cn'
import type { ToolActivity as ToolActivityType } from '../types'
import {
  CheckCircleIcon,
  CodeIcon,
  EyeIcon,
  RefreshIcon,
  XCircleIcon,
} from './Icons'

interface Props {
  tool: ToolActivityType
  onOpenFile?: (path: string) => void
}

export function ToolActivityChip({ tool, onOpenFile }: Props) {
  const isWrite = tool.name === 'file_write'
  const isEdit = tool.name === 'file_editor'
  const isInsert = tool.name === 'insert_after_line'
  const verb = isWrite
    ? 'create'
    : isEdit
      ? 'edit'
      : isInsert
        ? 'insert'
        : tool.name === 'file_read'
          ? 'read'
          : tool.name
  const path = tool.filePath ?? tool.display.replace(/^[^:]*:\s*/, '')

  const statusColor =
    tool.status === 'success'
      ? 'border-emerald-500/25 bg-emerald-500/[0.06]'
      : tool.status === 'error'
      ? 'border-destructive/30 bg-destructive/[0.06]'
      : 'border-primary/25 bg-primary/[0.06]'

  const clickable = Boolean(path && onOpenFile)

  return (
    <div
      className={cn(
        'inline-flex max-w-full items-center gap-2 rounded-xl border px-2.5 py-1.5 transition-all duration-200',
        statusColor,
        clickable && 'cursor-pointer hover:brightness-125',
      )}
      onClick={() => clickable && path && onOpenFile?.(path)}
      title={tool.result || path}
    >
      <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white/5">
        {isWrite || isEdit || isInsert ? (
          <CodeIcon className="h-3 w-3 text-blue-400" />
        ) : (
          <EyeIcon className="h-3 w-3 text-accent" />
        )}
      </span>
      <span className="font-mono text-[11px] text-muted-foreground">{verb}:</span>
      <span className="truncate font-mono text-[11px] text-foreground/90 max-w-[220px]">
        {path}
      </span>
      <span className="ml-0.5 flex items-center">
        {tool.status === 'running' && (
          <RefreshIcon className="h-3.5 w-3.5 animate-spin text-primary" />
        )}
        {tool.status === 'success' && (
          <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500" />
        )}
        {tool.status === 'error' && (
          <XCircleIcon className="h-3.5 w-3.5 text-destructive" />
        )}
      </span>
    </div>
  )
}
