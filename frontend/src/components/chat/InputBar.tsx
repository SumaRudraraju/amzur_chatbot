import { useState } from "react"
import type { FormEvent } from "react"

interface InputBarProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function InputBar({ onSend, disabled = false }: InputBarProps) {
  const [draft, setDraft] = useState("")

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || disabled) {
      return
    }
    onSend(trimmed)
    setDraft("")
  }

  return (
    <form onSubmit={handleSubmit} className="input-bar">
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Type your message..."
        className="input-field"
        disabled={disabled}
      />
      <button type="submit" className="send-button" disabled={disabled}>
        Send
      </button>
    </form>
  )
}
