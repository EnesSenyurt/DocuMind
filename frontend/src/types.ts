// Mirrors the backend Pydantic schemas (app/models).

export interface DocumentMeta {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  num_pages: number | null
  num_chunks: number
  created_at: string
}

export interface DocumentListResponse {
  documents: DocumentMeta[]
  total: number
}

export interface IngestResponse {
  document: DocumentMeta
}

export interface Citation {
  marker: number
  document_id: string
  filename: string
  page: number | null
  section: string | null
  score: number
  snippet: string
}

export interface ChatResponse {
  conversation_id: string
  message: string
  citations: Citation[]
  grounded: boolean
}

// UI-side chat message (assistant messages may carry citations).
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  grounded?: boolean
  pending?: boolean
  error?: boolean
}
