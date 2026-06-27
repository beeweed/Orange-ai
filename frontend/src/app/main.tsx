// Application entry point. Mounts the active route component into #root.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { resolveRoute } from './routes'

const Route = resolveRoute(window.location.pathname).component

const container = document.getElementById('root')
if (!container) {
  throw new Error('Root container #root not found')
}

createRoot(container).render(
  <StrictMode>
    <Route />
  </StrictMode>,
)
