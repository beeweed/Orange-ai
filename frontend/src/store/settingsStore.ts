// Settings store: persists provider/API keys/model/template to localStorage.
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AppSettings, ModelInfo, Provider } from '../types'

interface SettingsState extends AppSettings {
  // Cached model lists per provider (not persisted long-term but kept in memory).
  models: ModelInfo[]
  modelsLoading: boolean
  modelsError: string | null

  setProvider: (p: Provider) => void
  setOpenrouterApiKey: (k: string) => void
  setNvidiaApiKey: (k: string) => void
  setE2bApiKey: (k: string) => void
  setSandboxTemplate: (t: string) => void
  setModel: (m: string) => void
  setModels: (m: ModelInfo[]) => void
  setModelsLoading: (b: boolean) => void
  setModelsError: (e: string | null) => void

  activeApiKey: () => string
  isConfigured: () => boolean
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      provider: 'openrouter',
      openrouterApiKey: '',
      nvidiaApiKey: '',
      e2bApiKey: '',
      sandboxTemplate: '',
      model: '',
      models: [],
      modelsLoading: false,
      modelsError: null,

      setProvider: (provider) => set({ provider, models: [], model: '' }),
      setOpenrouterApiKey: (openrouterApiKey) => set({ openrouterApiKey }),
      setNvidiaApiKey: (nvidiaApiKey) => set({ nvidiaApiKey }),
      setE2bApiKey: (e2bApiKey) => set({ e2bApiKey }),
      setSandboxTemplate: (sandboxTemplate) => set({ sandboxTemplate }),
      setModel: (model) => set({ model }),
      setModels: (models) => set({ models }),
      setModelsLoading: (modelsLoading) => set({ modelsLoading }),
      setModelsError: (modelsError) => set({ modelsError }),

      activeApiKey: () => {
        const s = get()
        return s.provider === 'openrouter' ? s.openrouterApiKey : s.nvidiaApiKey
      },
      isConfigured: () => {
        const s = get()
        const key = s.provider === 'openrouter' ? s.openrouterApiKey : s.nvidiaApiKey
        return Boolean(key && s.model && s.e2bApiKey)
      },
    }),
    {
      name: 'vibe-coder-settings',
      // Persist only credentials/selection, not transient model lists.
      partialize: (s) => ({
        provider: s.provider,
        openrouterApiKey: s.openrouterApiKey,
        nvidiaApiKey: s.nvidiaApiKey,
        e2bApiKey: s.e2bApiKey,
        sandboxTemplate: s.sandboxTemplate,
        model: s.model,
      }),
    },
  ),
)
