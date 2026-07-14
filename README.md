# DocuMind

Chat with your own documents — a self-hosted RAG (Retrieval-Augmented Generation) knowledge assistant.

Upload PDFs, DOCX, TXT, or Markdown files and ask questions about them. Answers are grounded in your documents with mandatory source citations; if the documents don't contain the answer, DocuMind says so instead of hallucinating.

> **Status: work in progress.** Phases 1–2 are done: project skeleton + config + Docker, and the full ingestion pipeline (upload → extract → chunk → embed → store) with document management endpoints. Retrieval/chat, the chat UI, and the eval module land in the next phases, and this README will grow an architecture diagram, screenshots, and a design-decisions section alongside them.

## Stack

- **Backend:** Python 3.11, FastAPI, ChromaDB (embedded), sentence-transformers
- **LLM:** Gemini Flash by default, behind a provider interface (OpenAI/Anthropic swappable via config)
- **Frontend:** React + TypeScript + Vite
- **Infra:** Docker Compose, `.env`-based configuration

## Quickstart

```bash
cp .env.example .env   # then set GEMINI_API_KEY

# Production-style (built images, frontend on http://localhost:3000)
docker compose up --build

# Development (hot reload, frontend on http://localhost:5173)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Backend API docs: http://localhost:8000/docs — health check at `GET /api/health`.

## API (so far)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness + version |
| `POST` | `/api/documents` | Upload a PDF/DOCX/TXT/MD file; ingests and returns document metadata |
| `GET` | `/api/documents` | List ingested documents |
| `DELETE` | `/api/documents/{id}` | Remove a document and its vectors |

Upload rejects unsupported types with `415` and empty/text-less files with `422`.

## Running without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
pytest
```

## Configuration

All settings live in `.env` (see `.env.example`): LLM provider/model and API keys, embedding model, chunk size/overlap, retrieval top-k and relevance threshold, and data directory.
