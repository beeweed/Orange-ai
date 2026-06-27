# Vibe Coder — Autonomous AI Coding Agent

A production-grade autonomous AI agent that can **write, read, and overwrite files**
inside a live **E2B sandbox**, driven by an LLM using **native tool calling** with
**real-time token-by-token SSE streaming**.

## Live URLs
- **Frontend (App)**: https://3000-ig2ebo5aavb1uuast6zzs-a402f90a.sandbox.novita.ai
- **Backend (API)**: https://8000-ig2ebo5aavb1uuast6zzs-a402f90a.sandbox.novita.ai
- **API Health**: https://8000-ig2ebo5aavb1uuast6zzs-a402f90a.sandbox.novita.ai/api/health

## Architecture
Two independently built and deployed services:

```
frontend/   React 18 + Vite + TypeScript + Tailwind + Radix UI + Zustand
backend/    Python 3.13 + FastAPI + Uvicorn + asyncio + Pydantic + E2B SDK
```

The frontend talks to the backend **only** via the URL configured in
`frontend/.env` (`VITE_BACKEND_URL`). No data is stored on the server — all
chat history and settings live in the browser's **localStorage**.

## Key Features
- **Two tools (native function calling)**
  - `file_write(file_path, content)` — create or overwrite any file (no limits).
  - `file_read(file_path)` — read any file, returned with line numbers; missing
    paths return a structured error so the agent loop continues.
- **E2B sandbox** — created automatically on the first message of a chat
  (1-hour timeout). Custom template id supported. Files the agent writes are
  created in the sandbox; reads come straight from the sandbox.
- **Autonomous loop** — Plan → Act → Observe → Reflect with a hard
  **max iteration limit of 1000** (shown at the top of the app, reset on every
  user message) and repeated-tool-call detection to avoid infinite loops.
- **Real-time streaming** — true token-by-token SSE from the backend; the stream
  pauses on a tool call and resumes after the result. "thinking..." and
  "creating sandbox..." animations with a shiny shimmer effect.
- **Providers** — OpenRouter and NVIDIA NIM (both OpenAI-compatible). Add an API
  key in Settings and fetch all available models. Easily extensible to more
  providers (add a client config in `backend/src/services/llm_service.py`).
- **Full memory** — the entire conversation (user input, assistant responses,
  tool calls + results) is preserved without truncation.
- **UI** — chat on the left (user messages in bubbles, assistant responses not),
  a VS Code-style file tree + code viewer on the right, minimal tool chips
  (`create: PATH` / `read: PATH`), settings dialog (Radix), and a localStorage
  chat-history sidebar with auto-naming + delete. Fully responsive with a mobile
  tab layout.

## API Endpoints
| Method | Path | Description |
| ------ | ---- | ----------- |
| GET  | `/api/health` | Liveness probe |
| GET  | `/api/ready` | Readiness probe |
| POST | `/api/models` | List provider models (`{provider, api_key}`) |
| POST | `/api/chat/stream` | Run one autonomous agent turn (SSE stream) |
| POST | `/api/sandbox/files` | Get sandbox file tree |
| POST | `/api/sandbox/file` | Read a single file's raw content |
| POST | `/api/sandbox/kill` | Terminate a sandbox |

## Configuration
- **Backend URL** is set ONLY in `frontend/.env`:
  ```
  VITE_BACKEND_URL=https://8000-ig2ebo5aavb1uuast6zzs-a402f90a.sandbox.novita.ai
  ```
- **API keys** (OpenRouter / NVIDIA / E2B) and the model are entered in the
  in-app **Settings** dialog and stored in the browser. They are sent per
  request and never persisted on the server.

## Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
# set VITE_BACKEND_URL in .env first
npm run dev        # dev server on :3000
# or
npm run build && npm run preview
```

## Tests
```bash
cd backend
python -m pytest src/tests -q
```

## Usage Guide
1. Open the app. The Settings dialog opens on first run.
2. Choose a provider, paste its API key, click **Fetch models**, select a model.
3. Paste your **E2B Sandbox API Key** (and optionally a custom template id).
4. Click **Done**, then describe what you want to build.
5. On your first message a sandbox is created ("creating sandbox..."), then the
   agent streams its work, writing files you can browse on the right.

## Tech Stack
- Frontend: React 18, Vite 5, TypeScript, TailwindCSS, Radix UI, Zustand
- Backend: FastAPI, Uvicorn, asyncio, Pydantic v2, httpx, E2B SDK, sse-starlette
