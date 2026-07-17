import { FormEvent, useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '../types'
import MessageBubble from './MessageBubble'

interface Props {
  messages: ChatMessage[]
  busy: boolean
  hasDocuments: boolean
  onSend: (message: string) => void
  onNewChat: () => void
}

export default function ChatPanel({
  messages,
  busy,
  hasDocuments,
  onSend,
  onNewChat,
}: Props) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  function submit(e: FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || busy) return
    onSend(trimmed)
    setInput('')
  }

  return (
    <section className="chat">
      <header className="chat-header">
        <div className="chat-header-title">
          <h1>Chat</h1>
          <span className="tagline">Answers grounded in your documents, with sources</span>
        </div>
        <button className="btn-ghost" onClick={onNewChat} disabled={messages.length === 0}>
          New chat
        </button>
      </header>

      <div className="messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-mark" aria-hidden="true" />
            <p className="empty-title">Ask a question about your documents</p>
            <p className="muted">
              {hasDocuments
                ? 'Every answer cites its sources — expand them under each reply.'
                : 'Upload a document from the sidebar to get started.'}
            </p>
          </div>
        ) : (
          <div className="messages-inner">
            {messages.map((message, i) => (
              <MessageBubble key={i} message={message} />
            ))}
          </div>
        )}
      </div>

      <form className="composer" onSubmit={submit}>
        <div className="composer-inner">
          <input
            type="text"
            value={input}
            placeholder={hasDocuments ? 'Ask a question…' : 'Upload a document first…'}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <button className="btn-accent" type="submit" disabled={busy || !input.trim()}>
            {busy ? '…' : 'Send'}
          </button>
        </div>
      </form>
    </section>
  )
}
