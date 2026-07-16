import { useCallback, useEffect, useState } from 'react'
import { ApiError, getConversation, listConversations, listDocuments, sendChat } from './api'
import ChatPanel from './components/ChatPanel'
import Sidebar from './components/Sidebar'
import type { ChatMessage, ConversationSummary, DocumentMeta } from './types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [conversationsLoading, setConversationsLoading] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refreshDocuments = useCallback(async () => {
    try {
      const data = await listDocuments()
      setDocuments(data.documents)
    } catch {
      // Backend may still be starting; leave the list as-is.
    } finally {
      setDocsLoading(false)
    }
  }, [])

  const refreshConversations = useCallback(async () => {
    try {
      const data = await listConversations()
      setConversations(data.conversations)
    } catch {
      // Backend may still be starting; leave the list as-is.
    } finally {
      setConversationsLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshDocuments()
    refreshConversations()
  }, [refreshDocuments, refreshConversations])

  async function handleSend(message: string) {
    setBusy(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message },
      { role: 'assistant', content: '', pending: true },
    ])
    try {
      const response = await sendChat(message, conversationId)
      const isNewConversation = response.conversation_id !== conversationId
      setConversationId(response.conversation_id)
      setMessages((prev) => {
        const next = prev.slice(0, -1) // drop the pending placeholder
        next.push({
          role: 'assistant',
          content: response.message,
          citations: response.citations,
          grounded: response.grounded,
        })
        return next
      })
      // A new conversation appeared, or an existing one's message count/title
      // changed — either way the sidebar list needs to catch up.
      if (isNewConversation) void refreshConversations()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Something went wrong.'
      setMessages((prev) => {
        const next = prev.slice(0, -1)
        next.push({ role: 'assistant', content: detail, error: true })
        return next
      })
    } finally {
      setBusy(false)
    }
  }

  function handleNewChat() {
    setMessages([])
    setConversationId(null)
  }

  async function handleSelectConversation(id: string) {
    if (id === conversationId) return
    try {
      const detail = await getConversation(id)
      setConversationId(id)
      setMessages(
        detail.messages.map((m) => ({
          role: m.role,
          content: m.content,
          citations: m.citations,
          grounded: m.role === 'assistant' ? m.citations.length > 0 : undefined,
        })),
      )
    } catch {
      // Conversation may have been deleted elsewhere; leave current view as-is.
    }
  }

  return (
    <div className="app">
      <Sidebar
        documents={documents}
        documentsLoading={docsLoading}
        onDocumentsChanged={refreshDocuments}
        conversations={conversations}
        conversationsLoading={conversationsLoading}
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
      />
      <ChatPanel
        messages={messages}
        busy={busy}
        hasDocuments={documents.length > 0}
        onSend={handleSend}
        onNewChat={handleNewChat}
      />
    </div>
  )
}
