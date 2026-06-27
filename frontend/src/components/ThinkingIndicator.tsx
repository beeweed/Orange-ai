// Animated "thinking..." / "creating sandbox..." indicator with shiny shimmer.
import { SparkIcon } from './Icons'

interface Props {
  label: string
  // When true, shows the spark glow + shimmer text (used for sandbox phase).
  variant?: 'dots' | 'shimmer'
}

export function ThinkingIndicator({ label, variant = 'dots' }: Props) {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center flex-shrink-0 animate-pulse-glow">
        <SparkIcon className="w-4 h-4 text-primary" />
      </div>
      {variant === 'dots' ? (
        <div className="flex items-center gap-2 px-1 py-2">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-primary thinking-dot animate-thinking-wave" />
            <span className="w-2 h-2 rounded-full bg-primary thinking-dot animate-thinking-wave" />
            <span className="w-2 h-2 rounded-full bg-primary thinking-dot animate-thinking-wave" />
          </div>
          <span className="shimmer-text text-sm font-medium">{label}</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 px-1 py-2">
          <span className="shimmer-text text-sm font-medium">{label}</span>
        </div>
      )}
    </div>
  )
}
