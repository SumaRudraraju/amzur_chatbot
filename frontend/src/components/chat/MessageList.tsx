import type { ChatMessage } from "../../types/chat"

interface MessageListProps {
  messages: ChatMessage[]
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

function renderMarkdown(text: string): string {
  const escaped = escapeHtml(text)
    .replace(/\r\n|\r|\n/g, "<br />")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>')

  return `<div class="message-text-markup">${escaped}</div>`
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.length === 0 ? <p className="empty-state">Start a new conversation to see messages here.</p> : null}
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message-item ${message.role === "assistant" ? "assistant-row" : "user-row"}`}
        >
          <div className={`message-avatar ${message.role === "assistant" ? "avatar-assistant" : "avatar-user"}`}>
            {message.role === "assistant" ? "AI" : "You"}
          </div>
          <div className={`message-bubble ${message.role === "assistant" ? "message-assistant" : "message-user"}`}>
            <div className="message-meta">
              <span className="message-role">{message.role === "assistant" ? "Assistant" : "You"}</span>
            </div>
            <div className="message-text">
              <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.text) }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
