import type {
  AuthRequest,
  ChatRequest,
  ChatResponse,
  ChatThread,
  PersistedChatRequest,
  PersistedChatResponse,
  StoredMessage,
  UserProfile,
} from "../types/chat"

interface PersistedChatStreamHandlers {
  onThreadId?: (threadId: string) => void
  onChunk: (chunk: string) => void
  onDone?: () => void
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    ...init,
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message = data?.error?.message ?? "Request failed."
    throw new Error(message)
  }

  return data as T
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export async function signupEmployee(payload: AuthRequest): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/auth/signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export async function signinEmployee(payload: AuthRequest): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/auth/signin", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const response = await fetch("/api/auth/me", { credentials: "include" })
  if (!response.ok) {
    throw new Error("Not authenticated")
  }
  const data = (await response.json()) as { user: UserProfile }
  return data.user
}

export async function logoutEmployee(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  })
}

export async function fetchThreads(): Promise<ChatThread[]> {
  return apiFetch<ChatThread[]>("/api/chat/threads")
}

export async function createThread(title?: string): Promise<ChatThread> {
  return apiFetch<ChatThread>("/api/chat/threads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  })
}

export async function updateThread(threadId: string, title: string): Promise<ChatThread> {
  return apiFetch<ChatThread>(`/api/chat/threads/${encodeURIComponent(threadId)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  })
}

export async function deleteThread(threadId: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/api/chat/threads/${encodeURIComponent(threadId)}`, {
    method: "DELETE",
  })
}

export async function fetchMessages(threadId: string): Promise<StoredMessage[]> {
  return apiFetch<StoredMessage[]>(`/api/chat/threads/${encodeURIComponent(threadId)}/messages`)
}

export async function sendPersistedChat(payload: PersistedChatRequest): Promise<PersistedChatResponse> {
  return apiFetch<PersistedChatResponse>("/api/chat/send", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

export async function sendPersistedChatStream(
  payload: PersistedChatRequest,
  handlers: PersistedChatStreamHandlers,
): Promise<void> {
  const response = await fetch("/api/chat/send/stream", {
    credentials: "include",
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const message = data?.error?.message ?? "Failed to stream chat response."
    throw new Error(message)
  }

  if (!response.body) {
    throw new Error("Streaming is not supported by this browser.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  const parseEvent = (eventBlock: string) => {
    let eventName = "message"
    const dataParts: string[] = []

    for (const line of eventBlock.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        dataParts.push(line.slice(5).trimStart())
      }
    }

    const data = dataParts.join("\n").replace(/\\n/g, "\n")

    if (eventName === "thread") {
      handlers.onThreadId?.(data)
      return
    }
    if (eventName === "chunk") {
      handlers.onChunk(data)
      return
    }
    if (eventName === "done") {
      handlers.onDone?.()
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })

    let separatorIndex = buffer.indexOf("\n\n")
    while (separatorIndex !== -1) {
      const block = buffer.slice(0, separatorIndex).trim()
      buffer = buffer.slice(separatorIndex + 2)
      if (block) {
        parseEvent(block)
      }
      separatorIndex = buffer.indexOf("\n\n")
    }
  }
}
