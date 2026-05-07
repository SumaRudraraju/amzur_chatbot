from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The user's chat message")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="The assistant's response")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None


class AuthStatusResponse(BaseModel):
    user: UserResponse


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_activity_at: str | None = None


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    role: str
    content: str
    created_at: str | None = None


class ThreadCreateRequest(BaseModel):
    title: str | None = None


class ThreadUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1)


class PersistedChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    thread_id: str | None = None


class PersistedChatResponse(BaseModel):
    answer: str
    thread_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
