export type ChatRole = "user" | "assistant"

export interface ChatMessage {
  id: string
  role: ChatRole
  text: string
}

export interface AuthRequest {
  email: string
  password: string
  full_name?: string
}

export interface UserProfile {
  id: string
  email: string
  full_name?: string | null
}

export interface ChatThread {
  id: string
  user_id: string
  title?: string | null
  created_at?: string | null
  updated_at?: string | null
  last_activity_at?: string | null
}

export interface StoredMessage {
  id: string
  thread_id: string
  user_id: string
  role: ChatRole
  content: string
  created_at?: string | null
}

export interface ChatRequest {
  prompt: string
}

export interface ChatResponse {
  answer: string
}

export interface PersistedChatRequest {
  prompt: string
  thread_id?: string
}

export interface PersistedChatResponse {
  answer: string
  thread_id: string
  user_message: StoredMessage
  assistant_message: StoredMessage
}

export interface ApiError {
  error: {
    code: string
    message: string
  }
}
