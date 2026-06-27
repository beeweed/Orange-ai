// Backend URL resolution. The backend URL is ONLY sourced from the .env file
// (VITE_BACKEND_URL). No other place may configure it.

const raw = import.meta.env.VITE_BACKEND_URL

if (!raw) {
  // Fail fast and loud in development so misconfiguration is obvious.
  // eslint-disable-next-line no-console
  console.error(
    'VITE_BACKEND_URL is not set. Configure it in frontend/.env',
  )
}

export const BACKEND_URL = (raw || 'http://localhost:8000').replace(/\/$/, '')

export const API = {
  health: `${BACKEND_URL}/api/health`,
  models: `${BACKEND_URL}/api/models`,
  chatStream: `${BACKEND_URL}/api/chat/stream`,
  sandboxFiles: `${BACKEND_URL}/api/sandbox/files`,
  sandboxFile: `${BACKEND_URL}/api/sandbox/file`,
  sandboxKill: `${BACKEND_URL}/api/sandbox/kill`,
} as const
