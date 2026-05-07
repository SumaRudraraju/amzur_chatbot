from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from ..dependencies.auth import get_current_user
from ..schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    MessageResponse,
    PersistedChatRequest,
    PersistedChatResponse,
    ThreadCreateRequest,
    ThreadResponse,
    ThreadUpdateRequest,
)
from ..services.chat_service import (
    create_thread_for_user,
    delete_thread_for_user,
    get_chat_response,
    get_messages_for_thread,
    get_threads_for_user,
    send_chat_message,
    update_thread_for_user,
)

router = APIRouter()


def _encode_sse(event: str, data: str) -> str:
    safe = data.replace("\r", "").replace("\n", "\\n")
    return f"event: {event}\\ndata: {safe}\\n\\n"


def _chunk_text(text: str, size: int = 42):
    for index in range(0, len(text), size):
        yield text[index : index + size]


def format_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def chat_endpoint(payload: ChatRequest):
    try:
        answer = get_chat_response(payload.prompt)
        return ChatResponse(answer=answer)
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to complete chat request.")


@router.get(
    "/api/chat/threads",
    response_model=list[ThreadResponse],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def list_threads_endpoint(current_user: dict = Depends(get_current_user)):
    try:
        rows = get_threads_for_user(str(current_user["id"]))
        return [
            ThreadResponse(
                id=str(item["id"]),
                user_id=str(item["user_id"]),
                title=item.get("title"),
                created_at=str(item.get("created_at")) if item.get("created_at") else None,
                updated_at=str(item.get("updated_at")) if item.get("updated_at") else None,
                last_activity_at=str(item.get("last_activity_at")) if item.get("last_activity_at") else None,
            )
            for item in rows
        ]
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to load threads.")


@router.post(
    "/api/chat/threads",
    response_model=ThreadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_thread_endpoint(payload: ThreadCreateRequest, current_user: dict = Depends(get_current_user)):
    try:
        row = create_thread_for_user(str(current_user["id"]), payload.title)
        return ThreadResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row.get("title"),
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
            updated_at=str(row.get("updated_at")) if row.get("updated_at") else None,
            last_activity_at=None,
        )
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to create thread.")


@router.put(
    "/api/chat/threads/{thread_id}",
    response_model=ThreadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def update_thread_endpoint(thread_id: str, payload: ThreadUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        row = update_thread_for_user(str(current_user["id"]), thread_id, payload.title)
        return ThreadResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row.get("title"),
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
            updated_at=str(row.get("updated_at")) if row.get("updated_at") else None,
            last_activity_at=None,
        )
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to update thread.")


@router.delete(
    "/api/chat/threads/{thread_id}",
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def delete_thread_endpoint(thread_id: str, current_user: dict = Depends(get_current_user)):
    try:
        delete_thread_for_user(str(current_user["id"]), thread_id)
        return {"deleted": True}
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to delete thread.")


@router.get(
    "/api/chat/threads/{thread_id}/messages",
    response_model=list[MessageResponse],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def list_messages_endpoint(thread_id: str, current_user: dict = Depends(get_current_user)):
    try:
        rows = get_messages_for_thread(user_id=str(current_user["id"]), thread_id=thread_id)
        return [
            MessageResponse(
                id=str(item["id"]),
                thread_id=str(item["thread_id"]),
                user_id=str(item["user_id"]),
                role=item["role"],
                content=item["content"],
                created_at=str(item.get("created_at")) if item.get("created_at") else None,
            )
            for item in rows
        ]
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to load messages.")


@router.post(
    "/api/chat/send",
    response_model=PersistedChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def send_persisted_chat_endpoint(payload: PersistedChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = send_chat_message(
            user_id=str(current_user["id"]),
            prompt=payload.prompt,
            thread_id=payload.thread_id,
        )
        return PersistedChatResponse(
            answer=result["answer"],
            thread_id=str(result["thread_id"]),
            user_message=MessageResponse(
                id=str(result["user_message"]["id"]),
                thread_id=str(result["user_message"]["thread_id"]),
                user_id=str(result["user_message"]["user_id"]),
                role=result["user_message"]["role"],
                content=result["user_message"]["content"],
                created_at=str(result["user_message"].get("created_at")) if result["user_message"].get("created_at") else None,
            ),
            assistant_message=MessageResponse(
                id=str(result["assistant_message"]["id"]),
                thread_id=str(result["assistant_message"]["thread_id"]),
                user_id=str(result["assistant_message"]["user_id"]),
                role=result["assistant_message"]["role"],
                content=result["assistant_message"]["content"],
                created_at=str(result["assistant_message"].get("created_at")) if result["assistant_message"].get("created_at") else None,
            ),
        )
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to complete chat request.")


@router.post(
    "/api/chat/send/stream",
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def send_persisted_chat_stream_endpoint(payload: PersistedChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = send_chat_message(
            user_id=str(current_user["id"]),
            prompt=payload.prompt,
            thread_id=payload.thread_id,
        )
    except ValueError as exc:
        return format_error(400, "invalid_input", str(exc))
    except Exception:
        return format_error(500, "internal_error", "Unable to complete chat request.")

    def event_generator():
        yield _encode_sse("thread", str(result["thread_id"]))
        answer = result.get("answer", "") or ""
        for piece in _chunk_text(answer):
            yield _encode_sse("chunk", piece)
        yield _encode_sse("done", "[DONE]")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
