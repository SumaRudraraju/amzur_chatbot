# Amzur AI Chat

A lightweight AI chatbot application using React + TypeScript + Tailwind CSS for the frontend and FastAPI + Python for the backend.

The app sends user chat messages from the React UI to a FastAPI backend, which forwards them to an LLM via LangChain and the Amzur LiteLLM Proxy.

## Architecture

- `Frontend/`
  - React UI built with Vite
  - Chat page and message components under `src/components/chat`
  - API access centralized in `src/lib/api.ts`
  - Types defined in `src/types/chat.ts`

- `Backend/`
  - FastAPI service
  - Chat endpoint at `POST /api/chat`
  - Business logic in `app/services/chat_service.py`
  - Prompt builder in `app/ai/chains/chat_chain.py`
  - Prompt template in `app/ai/prompts/basic_chat.txt`
  - LiteLLM proxy wrapper in `app/ai/llm.py`

## Requirements

- Python 3.11+
- Node.js 18+ / npm
- `Backend/requirements.txt` includes FastAPI, Pydantic, and pydantic-settings
- Frontend dependencies are managed in `frontend/package.json`

## Backend Setup

1. Create and activate a Python virtual environment inside `Backend/`.
2. Install dependencies:
   ```bash
   cd Backend
   python -m pip install -r requirements.txt
   ```
3. Configure environment variables in `Backend/.env`:
   - `LITELLM_PROXY_URL` (example: `https://litellm.amzur.com`)
   - `LITELLM_API_KEY`
   - `LLM_MODEL` (example: `gemini/gemini-2.5-flash`)
   - `LITELLM_USER_ID`

4. Run the backend:
   ```bash
   cd Backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Frontend Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Run the frontend development server:
   ```bash
   npm run dev
   ```
3. Open the app in your browser at the Vite URL, typically `http://localhost:5173`

> The frontend is configured to proxy `/api` requests to `http://localhost:8000`, so the chat UI can call the backend without browser CORS errors.

## Usage

- Type a message in the chat input.
- Messages are sent to `POST /api/chat`.
- The backend sends the message to the LiteLLM proxy and returns the assistant response.
- The chat UI displays user and assistant messages with markdown-safe rendering.

## Notes

- All AI requests are routed through the Amzur LiteLLM Proxy.
- The backend does not call Gemini or other providers directly.
- Business logic is separated from the API/router layer.
- Errors are returned in structured JSON format.
