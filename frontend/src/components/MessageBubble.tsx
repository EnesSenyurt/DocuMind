import type { ChatMessage } from '../types'
import Citations from './Citations'

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const classes = ['message', isUser ? 'message-user' : 'message-assistant']
  if (message.error) classes.push('message-error')
  if (message.grounded === false) classes.push('message-noinfo')

  return (
    <div className={classes.join(' ')}>
      <div className="message-role">{isUser ? 'You' : 'DocuMind'}</div>
      <div className="message-content">
        {message.pending ? (
          <span className="typing">
            <span></span>
            <span></span>
            <span></span>
          </span>
        ) : (
          message.content
        )}
      </div>
      {message.citations && message.citations.length > 0 && (
        <Citations citations={message.citations} />
      )}
    </div>
  )
}
