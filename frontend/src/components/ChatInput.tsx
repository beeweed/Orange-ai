// Chat input: auto-growing textarea + send button. Enter sends, Shift+Enter
// inserts a newline. Disabled while a run is in progress or unconfigured.
import { useEffect, useRef, useState } from 'react'
import { cn } from '../utils/cn'
import { SendIcon } from './Icons'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
  running?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, running, placeholder }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  const submit = () => {
    const text = value.trim()
    if (!text || disabled || running) return
    onSend(text)
    setValue('')
  }

  return (
    <div className="p-4 bg-[#252525] border-t border-border/30">
      <div className="relative">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder={placeholder ?? 'Describe what you want to build...'}
          rows={3}
          className="w-full min-h-[100px] max-h-[200px] bg-[#323234] rounded-2xl px-4 py-4 pr-14 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 border border-transparent focus:border-primary/30 transition-all"
        />
        <button
          onClick={submit}
          disabled={disabled || running || !value.trim()}
          className={cn(
            'absolute bottom-3 right-3 h-10 w-10 rounded-xl flex items-center justify-center shadow-md transition-all duration-200 active:scale-[0.98]',
            disabled || running || !value.trim()
              ? 'bg-primary/40 cursor-not-allowed'
              : 'bg-primary hover:bg-primary/90 shadow-primary/20 hover:shadow-lg hover:shadow-primary/30',
          )}
          title={running ? 'Agent is running' : 'Send'}
        >
          <SendIcon className="w-5 h-5 text-white" />
        </button>
      </div>
    </div>
  )
}
