from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text

from ..core.settings import settings

_engine = None


def _normalize_supabase_url(raw_url: str) -> str:
    value = (raw_url or "").strip()
    value = value.replace(" @", "@").replace("\t", "")
    return value


def _get_engine():
    global _engine
    if _engine is None:
        db_url = _normalize_supabase_url(settings.SUPABASE_URL)
        if not db_url:
            raise RuntimeError("SUPABASE_URL is required.")
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def _row_to_dict(row: Any) -> dict:
    return dict(row._mapping)


def create_user(email: str, password_hash: str, full_name: str | None = None) -> dict:
    query = text(
        """
        INSERT INTO users (email, password_hash, full_name)
        VALUES (:email, :password_hash, :full_name)
        RETURNING id, email, full_name, created_at
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"email": email, "password_hash": password_hash, "full_name": full_name}).first()
    if not row:
        raise RuntimeError("Failed to create user.")
    return _row_to_dict(row)


def get_user_by_email(email: str) -> dict | None:
    query = text(
        """
        SELECT id, email, full_name, password_hash
        FROM users
        WHERE email = :email AND is_active = TRUE
        LIMIT 1
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"email": email}).first()
    return _row_to_dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    query = text(
        """
        SELECT id, email, full_name
        FROM users
        WHERE id = CAST(:user_id AS UUID) AND is_active = TRUE
        LIMIT 1
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"user_id": user_id}).first()
    return _row_to_dict(row) if row else None


def mark_last_login(user_id: str) -> None:
    query = text(
        """
        UPDATE users
        SET last_login_at = CURRENT_TIMESTAMP
        WHERE id = CAST(:user_id AS UUID)
        """
    )
    with _get_engine().begin() as conn:
        conn.execute(query, {"user_id": user_id})


def create_auth_session(session_id: str, user_id: str, expires_at_unix: int) -> None:
    expires_at = datetime.fromtimestamp(expires_at_unix, tz=timezone.utc)
    query = text(
        """
        INSERT INTO sessions (id, user_id, expires_at, is_revoked)
        VALUES (CAST(:session_id AS UUID), CAST(:user_id AS UUID), :expires_at, FALSE)
        ON CONFLICT (id) DO UPDATE SET
          user_id = EXCLUDED.user_id,
          expires_at = EXCLUDED.expires_at,
          is_revoked = FALSE
        """
    )
    with _get_engine().begin() as conn:
        conn.execute(query, {"session_id": session_id, "user_id": user_id, "expires_at": expires_at})


def revoke_auth_session(session_id: str) -> None:
    query = text(
        """
        UPDATE sessions
        SET is_revoked = TRUE
        WHERE id = CAST(:session_id AS UUID)
        """
    )
    with _get_engine().begin() as conn:
        conn.execute(query, {"session_id": session_id})


def is_session_active(session_id: str) -> bool:
    query = text(
        """
        SELECT id
        FROM sessions
        WHERE id = CAST(:session_id AS UUID)
          AND is_revoked = FALSE
          AND expires_at > CURRENT_TIMESTAMP
        LIMIT 1
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"session_id": session_id}).first()
    return row is not None


def create_thread(user_id: str, title: str | None = None) -> dict:
    query = text(
        """
        INSERT INTO threads (user_id, title)
        VALUES (CAST(:user_id AS UUID), :title)
        RETURNING id, user_id, title, created_at, updated_at
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"user_id": user_id, "title": title}).first()
    if not row:
        raise RuntimeError("Failed to create thread.")
    return _row_to_dict(row)


def list_threads(user_id: str) -> list[dict]:
    query = text(
        """
        SELECT t.id, t.user_id, COALESCE(t.title, 'Untitled thread') AS title, t.created_at, t.updated_at,
          COALESCE(m.last_message_at, t.created_at) AS last_activity_at
        FROM threads t
        LEFT JOIN (
          SELECT thread_id, MAX(created_at) AS last_message_at
          FROM messages
          GROUP BY thread_id
        ) m ON m.thread_id = t.id
        WHERE t.user_id = CAST(:user_id AS UUID)
        ORDER BY COALESCE(m.last_message_at, t.created_at) DESC
        """
    )
    with _get_engine().begin() as conn:
        rows = conn.execute(query, {"user_id": user_id}).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_thread_for_user(thread_id: str, user_id: str) -> dict | None:
    query = text(
        """
        SELECT id, user_id, title, created_at, updated_at
        FROM threads
        WHERE id = CAST(:thread_id AS UUID)
          AND user_id = CAST(:user_id AS UUID)
        LIMIT 1
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(query, {"thread_id": thread_id, "user_id": user_id}).first()
    return _row_to_dict(row) if row else None


def list_messages(thread_id: str, user_id: str) -> list[dict]:
    query = text(
        """
        SELECT m.id, m.thread_id, m.user_id, m.role, m.content, m.created_at
        FROM messages m
        INNER JOIN threads t ON t.id = m.thread_id
        WHERE m.thread_id = CAST(:thread_id AS UUID)
          AND t.user_id = CAST(:user_id AS UUID)
        ORDER BY m.created_at ASC
        """
    )
    with _get_engine().begin() as conn:
        rows = conn.execute(query, {"thread_id": thread_id, "user_id": user_id}).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_message(thread_id: str, user_id: str, role: str, content: str) -> dict:
    query = text(
        """
        INSERT INTO messages (thread_id, user_id, role, content)
        VALUES (CAST(:thread_id AS UUID), CAST(:user_id AS UUID), :role, :content)
        RETURNING id, thread_id, user_id, role, content, created_at
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(
            query,
            {
                "thread_id": thread_id,
                "user_id": user_id,
                "role": role,
                "content": content,
            },
        ).first()
    if not row:
        raise RuntimeError("Failed to save message.")
    return _row_to_dict(row)


def set_thread_title_if_empty(thread_id: str, title: str) -> None:
    query = text(
        """
        UPDATE threads
        SET title = :title
        WHERE id = CAST(:thread_id AS UUID)
          AND (title IS NULL OR LENGTH(TRIM(title)) = 0)
        """
    )
    with _get_engine().begin() as conn:
        conn.execute(query, {"thread_id": thread_id, "title": title})


def update_thread_title(thread_id: str, user_id: str, title: str) -> dict | None:
    query = text(
        """
        UPDATE threads
        SET title = :title, updated_at = CURRENT_TIMESTAMP
        WHERE id = CAST(:thread_id AS UUID)
          AND user_id = CAST(:user_id AS UUID)
        RETURNING id, user_id, title, created_at, updated_at
        """
    )
    with _get_engine().begin() as conn:
        row = conn.execute(
            query,
            {"thread_id": thread_id, "user_id": user_id, "title": title},
        ).first()
    return _row_to_dict(row) if row else None


def delete_thread(thread_id: str, user_id: str) -> bool:
    query = text(
        """
        DELETE FROM threads
        WHERE id = CAST(:thread_id AS UUID)
          AND user_id = CAST(:user_id AS UUID)
        """
    )
    with _get_engine().begin() as conn:
        result = conn.execute(query, {"thread_id": thread_id, "user_id": user_id})
    return result.rowcount > 0
