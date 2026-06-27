// Message renderers.
// - User messages are shown in a bubble (right-aligned).
// - Assistant messages are NOT in bubbles; they flow as plain content with an
//   iteration badge, tool chips, and markdown-rendered text.
import { memo } from 'react'
import type { ChatMessage } from '../types'
import { renderMarkdown } from '../utils/markdown'
import { SparkIcon, UserIcon } from './Icons'
import { ToolActivityChip } from './ToolActivity'

export const UserMessage = memo(function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex gap-3 justify-end animate-fade-in">
      <div className="max-w-[85%] px-4 py-3 rounded-2xl rounded-tr-md bg-primary text-primary-foreground shadow-lg shadow-primary/10">
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
      </div>
      <div className="w-8 h-8 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
        <UserIcon className="w-4 h-4 text-primary" />
      </div>
    </div>
  )
})

interface AssistantProps {
  message: ChatMessage
  streaming?: boolean
  onOpenFile?: (path: string) => void
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  streaming,
  onOpenFile,
}: AssistantProps) {
  const hasContent = Boolean(message.content)
  const hasTools = Boolean(message.tools && message.tools.length > 0)

  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center flex-shrink-0">
        <SparkIcon className="w-4 h-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-muted-foreground mb-2 block">
          Vibe Coder
        </span>

        {typeof message.iteration === 'number' && message.iteration > 0 && (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg bg-primary/10 border border-primary/20 mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-[10px] font-medium text-primary">
              Iteration {message.iteration}/1000
            </span>
          </div>
        )}

        {hasTools && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.tools!.map((t) => (
              <ToolActivityChip key={t.id} tool={t} onOpenFile={onOpenFile} />
            ))}
          </div>
        )}

        {hasContent && (
          <div
            className={
              'md-content max-w-none text-sm leading-relaxed text-foreground/90 ' +
              (streaming ? 'stream-caret' : '')
            }
            dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
          />
        )}
      </div>
    </div>
  )
})
