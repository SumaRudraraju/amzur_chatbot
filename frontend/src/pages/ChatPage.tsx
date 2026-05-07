import { useEffect, useMemo, useState } from "react"
import type { FormEvent } from "react"
import {
  createThread,
  deleteThread,
  fetchCurrentUser,
  fetchMessages,
  fetchThreads,
  logoutEmployee,
  sendPersistedChatStream,
  signinEmployee,
  signupEmployee,
  updateThread,
} from "../lib/api"
import type { ChatMessage, ChatThread, UserProfile } from "../types/chat"
import MessageList from "../components/chat/MessageList"
import InputBar from "../components/chat/InputBar"

const initialMessages: ChatMessage[] = []

const createMessage = (role: ChatMessage["role"], text: string): ChatMessage => ({
  id: crypto.randomUUID?.() ?? String(Date.now()),
  role,
  text,
})

export default function ChatPage() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [fullName, setFullName] = useState("")

  const [threads, setThreads] = useState<ChatThread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionChecked, setSessionChecked] = useState(false)

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) ?? null,
    [threads, activeThreadId],
  )

  const loadMessages = async (threadId: string) => {
    const history = await fetchMessages(threadId)
    setActiveThreadId(threadId)
    setMessages(
      history.map((item) => ({
        id: item.id,
        role: item.role,
        text: item.content,
      })),
    )
  }

  const loadThreads = async () => {
    const threadRows = await fetchThreads()
    setThreads(threadRows)
    if (threadRows.length > 0) {
      const preferredThreadId = activeThreadId && threadRows.some((item) => item.id === activeThreadId)
        ? activeThreadId
        : threadRows[0].id
      await loadMessages(preferredThreadId)
    } else {
      setActiveThreadId(null)
      setMessages([])
    }
  }

  useEffect(() => {
    const bootstrapSession = async () => {
      try {
        const me = await fetchCurrentUser()
        setUser(me)
        await loadThreads()
      } catch {
        setUser(null)
      } finally {
        setSessionChecked(true)
      }
    }

    void bootstrapSession()
  }, [])

  const handleAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const payload = {
        email,
        password,
        ...(authMode === "signup" && fullName.trim() ? { full_name: fullName.trim() } : {}),
      }
      const profile = authMode === "signup" ? await signupEmployee(payload) : await signinEmployee(payload)
      setUser(profile)
      await loadThreads()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to authenticate.")
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await logoutEmployee()
    setUser(null)
    setThreads([])
    setActiveThreadId(null)
    setMessages([])
    setError(null)
  }

  const handleGoogleLogin = async () => {
    setError(null)
    const popup = window.open("/api/auth/google/login", "googleLogin", "width=520,height=700")
    if (!popup) {
      setError("Popup blocked. Please allow popups and try again.")
      return
    }

    const onMessage = (event: MessageEvent) => {
      const allowedOrigins = new Set([window.location.origin, "http://localhost:8000"])
      if (!allowedOrigins.has(event.origin)) {
        return
      }

      const data = event.data as { type?: string; user?: UserProfile; error?: string }
      if (data.type === "amzur_google_auth_success" && data.user) {
        setUser(data.user)
        void loadThreads()
        window.removeEventListener("message", onMessage)
      }
      if (data.type === "amzur_google_auth_error") {
        setError(data.error || "Google login failed.")
        window.removeEventListener("message", onMessage)
      }
    }

    window.addEventListener("message", onMessage)
  }

  const handleCreateThread = async () => {
    if (!user) return
    setError(null)
    setLoading(true)
    try {
      const created = await createThread("New chat")
      await loadThreads()
      await loadMessages(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create thread.")
    } finally {
      setLoading(false)
    }
  }

  const handleRenameThread = async (threadId: string, currentTitle?: string | null) => {
    if (!user) return
    const nextTitle = window.prompt("Rename thread", currentTitle || "")
    if (!nextTitle) return
    setError(null)
    try {
      await updateThread(threadId, nextTitle)
      await loadThreads()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to rename thread.")
    }
  }

  const handleDeleteThread = async (threadId: string) => {
    if (!user) return
    if (!window.confirm("Delete this thread?")) return

    setError(null)
    try {
      await deleteThread(threadId)
      await loadThreads()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete thread.")
    }
  }

  const handleSend = async (messageText: string) => {
    if (!user) {
      setError("Please sign in first.")
      return
    }

    setError(null)
    setLoading(true)

    try {
      const userMessage = createMessage("user", messageText)
      const assistantMessageId = crypto.randomUUID?.() ?? `assistant-${Date.now()}`
      setMessages((current) => [...current, userMessage, { id: assistantMessageId, role: "assistant", text: "" }])

      let resolvedThreadId: string | null = activeThreadId

      await sendPersistedChatStream(
        {
          prompt: messageText,
          thread_id: activeThreadId ?? undefined,
        },
        {
          onThreadId: (threadId) => {
            resolvedThreadId = threadId
            setActiveThreadId(threadId)
          },
          onChunk: (chunk) => {
            setMessages((current) =>
              current.map((entry) =>
                entry.id === assistantMessageId ? { ...entry, text: entry.text + chunk } : entry,
              ),
            )
          },
        },
      )

      if (resolvedThreadId && (!activeThreadId || activeThreadId !== resolvedThreadId)) {
        await loadMessages(resolvedThreadId)
      }

      await loadThreads()
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.")
    } finally {
      setLoading(false)
    }
  }

  if (!sessionChecked) {
    return (
      <main className="app-shell">
        <section className="auth-shell">
          <div className="auth-panel">
            <div className="auth-card">
              <p className="status-line">Loading session...</p>
            </div>
          </div>
        </section>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="app-shell">
        <section className="auth-shell">
          <div className="auth-showcase">
            <p className="auth-showcase-label">AMZUR AI WORKSPACE</p>
            <h1 className="auth-showcase-title">One place for employee conversations, context, and AI responses.</h1>
            <p className="auth-showcase-text">
              Securely continue your previous threads, collaborate with prompts, and keep your chat history connected to your profile.
            </p>
            <div className="auth-showcase-grid">
              <div className="auth-showcase-card">
                <p className="auth-showcase-card-title">Thread Memory</p>
                <p className="auth-showcase-card-text">Pick up exactly where you left off across devices.</p>
              </div>
              <div className="auth-showcase-card">
                <p className="auth-showcase-card-title">Google + Password Login</p>
                <p className="auth-showcase-card-text">Flexible employee access with domain-based controls.</p>
              </div>
              <div className="auth-showcase-card">
                <p className="auth-showcase-card-title">LiteLLM Powered</p>
                <p className="auth-showcase-card-text">Keep your existing AI flow with improved UX and persistence.</p>
              </div>
            </div>
          </div>

          <div className="auth-panel">
            <div className="auth-card">
              <p className="chat-label auth-card-label">Welcome Back</p>
              <h2 className="auth-card-title">{authMode === "signin" ? "Sign in to continue" : "Create your account"}</h2>
              <p className="auth-subtitle">Use your employee email to access your chat history and assistant workspace.</p>

              <form onSubmit={handleAuth} className="auth-form">
                {authMode === "signup" ? (
                  <input
                    className="input-field"
                    placeholder="Full name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                  />
                ) : null}
                <input
                  className="input-field"
                  placeholder="Employee email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <input
                  className="input-field"
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button type="submit" className="send-button" disabled={loading}>
                  {loading ? "Please wait..." : authMode === "signin" ? "Sign in" : "Sign up"}
                </button>
              </form>

              <div className="auth-divider"><span>or</span></div>

              <button className="google-button" onClick={() => void handleGoogleLogin()} type="button">
                Continue with Google
              </button>
              <button
                className="auth-switch"
                onClick={() => setAuthMode((current) => (current === "signin" ? "signup" : "signin"))}
                type="button"
              >
                {authMode === "signin" ? "Need an account? Sign up" : "Have an account? Sign in"}
              </button>
              {error ? <p className="status-line auth-error">{error}</p> : null}
            </div>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <section className="chat-panel">
        <div className="chat-card">
          <header className="chat-header">
            <div>
              <p className="chat-label">AI Assistant</p>
              <h1 className="chat-title">Amzur AI Chat</h1>
            </div>
            <p className="chat-description">
              Signed in as {user.email}. Select a previous thread or send a new message. Responses still use your existing LiteLLM flow.
            </p>
            <div className="header-actions">
              <button className="ghost-button" onClick={() => void handleLogout()} type="button">
                Logout
              </button>
            </div>
          </header>

          <div className="chat-layout">
            <aside className="thread-sidebar">
              <div className="thread-sidebar-header">
                <p className="thread-heading">Previous Chats</p>
                <button className="thread-add" onClick={() => void handleCreateThread()} type="button">
                  + New
                </button>
              </div>
              <div className="thread-list">
                {threads.map((thread) => (
                  <div key={thread.id} className={`thread-item ${thread.id === activeThreadId ? "thread-item-active" : ""}`}>
                    <button
                      className="thread-open"
                      onClick={() => {
                        if (!user) return
                        void loadMessages(thread.id)
                      }}
                      type="button"
                    >
                      {thread.title || "Untitled thread"}
                    </button>
                    <div className="thread-actions">
                      <button type="button" className="thread-icon" onClick={() => void handleRenameThread(thread.id, thread.title)}>
                        Edit
                      </button>
                      <button type="button" className="thread-icon thread-danger" onClick={() => void handleDeleteThread(thread.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </aside>

            <div className="chat-body">
              {activeThread ? <p className="status-line">Thread: {activeThread.title || activeThread.id}</p> : null}
              <MessageList messages={messages} />
              <footer className="chat-footer">
                <InputBar onSend={handleSend} disabled={loading} />
                {loading ? <p className="status-line">Generating response…</p> : null}
                {error ? <p className="status-line auth-error">{error}</p> : null}
              </footer>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
