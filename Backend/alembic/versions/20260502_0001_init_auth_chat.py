"""init auth and chat tables

Revision ID: 20260502_0001
Revises: 
Create Date: 2026-05-02 20:00:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260502_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name VARCHAR(120),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMPTZ
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL,
            is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_messages_role CHECK (role IN ('user', 'assistant'))
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_messages_created_at;")
    op.execute("DROP INDEX IF EXISTS idx_messages_user_id;")
    op.execute("DROP INDEX IF EXISTS idx_messages_thread_id;")
    op.execute("DROP TABLE IF EXISTS messages;")

    op.execute("DROP INDEX IF EXISTS idx_threads_created_at;")
    op.execute("DROP INDEX IF EXISTS idx_threads_user_id;")
    op.execute("DROP TABLE IF EXISTS threads;")

    op.execute("DROP INDEX IF EXISTS idx_sessions_expires_at;")
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_id;")
    op.execute("DROP TABLE IF EXISTS sessions;")

    op.execute("DROP INDEX IF EXISTS idx_users_email;")
    op.execute("DROP TABLE IF EXISTS users;")
