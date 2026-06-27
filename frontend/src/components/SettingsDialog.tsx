// Settings dialog (Radix Dialog primitive).
// - Provider selection (OpenRouter / NVIDIA NIM) — extensible.
// - API key inputs (per provider) + E2B sandbox API key + optional template id.
// - Fetch all available models after a key is entered, with search + select.
import * as Dialog from '@radix-ui/react-dialog'
import { useMemo, useState } from 'react'
import { fetchModels } from '../lib/api'
import { useSettingsStore } from '../store/settingsStore'
import type { Provider } from '../types'
import { cn } from '../utils/cn'
import {
  CheckCircleIcon,
  CloseIcon,
  KeyIcon,
  RefreshIcon,
  SearchIcon,
  SettingsIcon,
  SparkIcon,
} from './Icons'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PROVIDERS: { id: Provider; label: string; hint: string; url: string }[] = [
  { id: 'openrouter', label: 'OpenRouter', hint: 'sk-or-v1-...', url: 'https://openrouter.ai/keys' },
  { id: 'nvidia', label: 'NVIDIA NIM', hint: 'nvapi-...', url: 'https://build.nvidia.com/settings/api-keys' },
]

export function SettingsDialog({ open, onOpenChange }: Props) {
  const s = useSettingsStore()
  const [search, setSearch] = useState('')

  const currentKey = s.provider === 'openrouter' ? s.openrouterApiKey : s.nvidiaApiKey

  const loadModels = async () => {
    if (!currentKey) {
      s.setModelsError('Enter an API key first.')
      return
    }
    s.setModelsError(null)
    s.setModelsLoading(true)
    try {
      const models = await fetchModels(s.provider, currentKey)
      s.setModels(models)
      if (models.length === 0) s.setModelsError('No models returned.')
    } catch (err) {
      s.setModelsError(err instanceof Error ? err.message : 'Failed to load models')
      s.setModels([])
    } finally {
      s.setModelsLoading(false)
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return s.models
    return s.models.filter(
      (m) => m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q),
    )
  }, [s.models, search])

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 bg-[#2d2d2d] rounded-2xl border border-border/30 shadow-2xl overflow-hidden focus:outline-none animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-border/30">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20">
                <SettingsIcon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-semibold text-foreground">
                  Settings
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground">
                  Configure your Vibe Coder
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
              <CloseIcon className="w-5 h-5" />
            </Dialog.Close>
          </div>

          {/* Content */}
          <form
            onSubmit={(e) => e.preventDefault()}
            className="p-6 space-y-6 max-h-[68vh] overflow-y-auto">
            {/* Provider selector */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <SparkIcon className="w-4 h-4 text-accent" />
                <label className="text-sm font-medium text-foreground">Provider</label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => s.setProvider(p.id)}
                    className={cn(
                      'rounded-xl border px-3 py-2.5 text-sm font-medium transition-all',
                      s.provider === p.id
                        ? 'bg-primary/15 border-primary/40 text-foreground'
                        : 'bg-[#363638] border-transparent text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* API key */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <KeyIcon className="w-4 h-4 text-primary" />
                <label className="text-sm font-medium text-foreground">
                  {s.provider === 'openrouter' ? 'OpenRouter' : 'NVIDIA NIM'} API Key
                </label>
              </div>
              <div className="bg-[#363638] rounded-xl p-4">
                <input
                  type="password"
                  placeholder={PROVIDERS.find((p) => p.id === s.provider)?.hint}
                  value={currentKey}
                  onChange={(e) =>
                    s.provider === 'openrouter'
                      ? s.setOpenrouterApiKey(e.target.value)
                      : s.setNvidiaApiKey(e.target.value)
                  }
                  className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
            </div>

            {/* E2B key */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <KeyIcon className="w-4 h-4 text-emerald-400" />
                <label className="text-sm font-medium text-foreground">E2B Sandbox API Key</label>
              </div>
              <div className="bg-[#363638] rounded-xl p-4">
                <input
                  type="password"
                  placeholder="e2b_..."
                  value={s.e2bApiKey}
                  onChange={(e) => s.setE2bApiKey(e.target.value)}
                  className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
            </div>

            {/* Sandbox template */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <SettingsIcon className="w-4 h-4 text-amber-400" />
                <label className="text-sm font-medium text-foreground">
                  Custom Sandbox Template ID <span className="text-muted-foreground">(optional)</span>
                </label>
              </div>
              <div className="bg-[#363638] rounded-xl p-4">
                <input
                  type="text"
                  placeholder="e.g. base, or your custom template id"
                  value={s.sandboxTemplate}
                  onChange={(e) => s.setSandboxTemplate(e.target.value)}
                  className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
            </div>

            {/* Model selection */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-foreground">Select Model</label>
                <button
                  onClick={loadModels}
                  disabled={s.modelsLoading}
                  className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline disabled:opacity-50"
                >
                  <RefreshIcon className={cn('w-3.5 h-3.5', s.modelsLoading && 'animate-spin')} />
                  {s.modelsLoading ? 'Loading...' : 'Fetch models'}
                </button>
              </div>

              <div className="relative">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search models..."
                  className="w-full bg-[#363638] rounded-lg pl-10 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {s.modelsError && (
                <p className="text-xs text-destructive">{s.modelsError}</p>
              )}

              <div className="bg-[#363638] rounded-xl max-h-[260px] overflow-y-auto p-2 space-y-1">
                {filtered.length === 0 && !s.modelsLoading && (
                  <p className="text-xs text-muted-foreground p-3">
                    {s.models.length === 0
                      ? 'Click "Fetch models" to load available models.'
                      : 'No models match your search.'}
                  </p>
                )}
                {filtered.map((m) => {
                  const isSel = s.model === m.id
                  return (
                    <div
                      key={m.id}
                      onClick={() => s.setModel(m.id)}
                      className={cn(
                        'flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors',
                        isSel
                          ? 'bg-primary/15 border border-primary/30'
                          : 'hover:bg-white/5 border border-transparent',
                      )}
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-foreground truncate">
                          {m.name}
                        </div>
                        <div className="text-[10px] text-muted-foreground truncate">{m.id}</div>
                      </div>
                      {isSel && <CheckCircleIcon className="w-5 h-5 text-primary shrink-0" />}
                    </div>
                  )
                })}
              </div>
            </div>
          </form>

          {/* Footer */}
          <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-border/30 bg-[#252525]">
            <span className="text-xs text-muted-foreground truncate">
              {s.model ? `Selected: ${s.model}` : 'No model selected'}
            </span>
            <Dialog.Close className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium shadow-md shadow-primary/20 hover:bg-primary/90 transition-all duration-200 active:scale-[0.98]">
              Done
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
