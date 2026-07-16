import { useCallback, useEffect, useState } from 'react'
import { ApiError, listDocuments, sendChat } from './api'
import ChatPanel from './components/ChatPanel'
import Sidebar from './components/Sidebar'
import type { ChatMessage, DocumentMeta } from './types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
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

  useEffect(() => {
    refreshDocuments()
  }, [refreshDocuments])

  async function handleSend(message: string) {
    setBusy(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message },
      { role: 'assistant', content: '', pending: true },
    ])
    try {
      const response = await sendChat(message, conversationId)
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

  return (
    <div className="app">
      <Sidebar documents={documents} loading={docsLoading} onChanged={refreshDocuments} />
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
