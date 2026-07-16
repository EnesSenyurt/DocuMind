import type {
  ChatResponse,
  ConversationDetail,
  ConversationListResponse,
  DocumentListResponse,
  IngestResponse,
} from './types'

// Vite proxies /api to the backend in dev; nginx does the same in prod.
const BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function parseError(response: Response): Promise<never> {
  let detail = `Request failed (${response.status})`
  try {
    const body = await response.json()
    if (body && typeof body.detail === 'string') detail = body.detail
  } catch {
    // non-JSON error body; keep the default message
  }
  throw new ApiError(response.status, detail)
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${BASE}/documents`)
  if (!response.ok) return parseError(response)
  return response.json()
}

export async function uploadDocument(file: File): Promise<IngestResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${BASE}/documents`, { method: 'POST', body: form })
  if (!response.ok) return parseError(response)
  return response.json()
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${BASE}/documents/${id}`, { method: 'DELETE' })
  if (!response.ok) return parseError(response)
}

export async function sendChat(
  message: string,
  conversationId: string | null,
): Promise<ChatResponse> {
  const response = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  })
  if (!response.ok) return parseError(response)
  return response.json()
}

export async function listConversations(): Promise<ConversationListResponse> {
  const response = await fetch(`${BASE}/conversations`)
  if (!response.ok) return parseError(response)
  return response.json()
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await fetch(`${BASE}/conversations/${id}`)
  if (!response.ok) return parseError(response)
  return response.json()
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`${BASE}/conversations/${id}`, { method: 'DELETE' })
  if (!response.ok) return parseError(response)
}
