import { useRef, useState } from 'react'
import { ApiError, deleteDocument, uploadDocument } from '../api'
import { timeAgo } from '../timeAgo'
import type { ConversationSummary, DocumentMeta } from '../types'

const ACCEPTED = '.pdf,.docx,.txt,.md,.markdown'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface Props {
  documents: DocumentMeta[]
  documentsLoading: boolean
  onDocumentsChanged: () => void
  conversations: ConversationSummary[]
  conversationsLoading: boolean
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
}

export default function Sidebar({
  documents,
  documentsLoading,
  onDocumentsChanged,
  conversations,
  conversationsLoading,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    setError(null)
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file)
      }
      onDocumentsChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function handleDelete(id: string) {
    setError(null)
    try {
      await deleteDocument(id)
      onDocumentsChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete failed')
    }
  }

  return (
    <aside className="sidebar">
      {/* Conversations: height-capped so it scrolls internally and never
          pushes the Documents section below out of view. */}
      <div className="conversations-section">
        <div className="sidebar-header">
          <h2>Conversations</h2>
        </div>
        <button className="btn-primary new-chat-btn" onClick={onNewChat}>
          + New chat
        </button>
        <div className="conversation-list">
          {conversationsLoading ? (
            <p className="muted">Loading…</p>
          ) : conversations.length === 0 ? (
            <p className="muted">No conversations yet.</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                className={
                  'conversation-item' + (conv.id === activeConversationId ? ' active' : '')
                }
                onClick={() => onSelectConversation(conv.id)}
              >
                <span className="conversation-title">{conv.title || 'New conversation'}</span>
                <span className="conversation-meta">
                  {conv.message_count} message{conv.message_count === 1 ? '' : 's'} ·{' '}
                  {timeAgo(conv.created_at)}
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Documents: always fully visible, scrolls internally on its own if long. */}
      <div className="documents-section">
        <div className="sidebar-header">
          <h2>Documents</h2>
          <button
            className="btn-primary"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : '+ Upload'}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            multiple
            hidden
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        <p className="sidebar-hint">PDF, DOCX, TXT, or Markdown</p>
        {error && <p className="sidebar-error">{error}</p>}

        <div className="doc-list">
          {documentsLoading ? (
            <p className="muted">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="muted">No documents yet. Upload one to start asking questions.</p>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="doc-item">
                <div className="doc-info">
                  <span className="doc-name" title={doc.filename}>
                    {doc.filename}
                  </span>
                  <span className="doc-meta">
                    {doc.num_chunks} chunk{doc.num_chunks > 1 ? 's' : ''}
                    {doc.num_pages != null ? ` · ${doc.num_pages}p` : ''} ·{' '}
                    {formatSize(doc.size_bytes)}
                  </span>
                </div>
                <button
                  className="doc-delete"
                  title="Delete document"
                  onClick={() => handleDelete(doc.id)}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  )
}
