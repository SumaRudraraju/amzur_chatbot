from ..ai.chains.chat_chain import run_chat_chain
from .store_service import (
    create_message,
    create_thread,
    delete_thread,
    get_thread_for_user,
    get_user_by_id,
    list_messages,
    list_threads,
    set_thread_title_if_empty,
    update_thread_title,
)


def get_chat_response(prompt: str) -> str:
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("Chat prompt must not be empty.")

    return run_chat_chain(normalized_prompt)


def get_threads_for_user(user_id: str) -> list[dict]:
    return list_threads(user_id)


def get_messages_for_thread(user_id: str, thread_id: str) -> list[dict]:
    return list_messages(thread_id=thread_id, user_id=user_id)


def create_thread_for_user(user_id: str, title: str | None = None) -> dict:
    return create_thread(user_id=user_id, title=title)


def update_thread_for_user(user_id: str, thread_id: str, title: str) -> dict:
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("Thread title must not be empty.")
    row = update_thread_title(thread_id=thread_id, user_id=user_id, title=normalized_title)
    if not row:
        raise ValueError("Thread not found.")
    return row


def delete_thread_for_user(user_id: str, thread_id: str) -> None:
    deleted = delete_thread(thread_id=thread_id, user_id=user_id)
    if not deleted:
        raise ValueError("Thread not found.")


def _auto_thread_title(prompt: str) -> str:
    cleaned = " ".join(prompt.strip().split())
    words = cleaned.split(" ")
    if len(words) > 8:
        cleaned = " ".join(words[:8])
    return cleaned[:80] if cleaned else "New chat"


def send_chat_message(user_id: str, prompt: str, thread_id: str | None = None) -> dict:
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("Chat prompt must not be empty.")

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")

    active_thread = get_thread_for_user(thread_id, user_id) if thread_id else None
    if not active_thread:
        auto_title = _auto_thread_title(normalized_prompt)
        active_thread = create_thread_for_user(user_id=user_id, title=auto_title)

    user_message = create_message(
        thread_id=active_thread["id"],
        user_id=user_id,
        role="user",
        content=normalized_prompt,
    )

    answer = run_chat_chain(user_message=normalized_prompt, user_email=user["email"])

    assistant_message = create_message(
        thread_id=active_thread["id"],
        user_id=user_id,
        role="assistant",
        content=answer,
    )

    set_thread_title_if_empty(active_thread["id"], _auto_thread_title(normalized_prompt))

    return {
        "answer": answer,
        "thread_id": active_thread["id"],
        "user_message": user_message,
        "assistant_message": assistant_message,
    }
