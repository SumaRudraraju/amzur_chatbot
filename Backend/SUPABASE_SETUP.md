# Amzur AI Chat - Supabase Database Setup Guide

## Overview

This guide explains how to set up and integrate the Supabase PostgreSQL database with the Amzur AI Chat application. The complete schema includes user management, conversations, messages, analytics, and more.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Project Setup](#supabase-project-setup)
3. [Running the Schema](#running-the-schema)
4. [Environment Configuration](#environment-configuration)
5. [Using the ORM Models](#using-the-orm-models)
6. [Integration with FastAPI](#integration-with-fastapi)
7. [Database Operations](#database-operations)
8. [Security & Row Level Security](#security--row-level-security)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

- Supabase account (https://supabase.com)
- Python 3.11+
- Required packages:
  ```bash
  pip install sqlalchemy sqlalchemy[asyncio] asyncpg pydantic pydantic-settings psycopg2-binary
  ```

## Supabase Project Setup

### Step 1: Create a Supabase Project

1. Log in to [Supabase Console](https://app.supabase.com)
2. Click "New Project"
3. Fill in project details:
   - **Name**: AIForgeTraining (or your preferred name)
   - **Database Password**: Create a strong password
   - **Region**: Select closest to your location
4. Click "Create new project" and wait for it to initialize

### Step 2: Get Your Credentials

Once your project is created:

1. Go to **Project Settings** → **Database**
2. You'll find:
   - **Host**: `[project-id].pooler.supabase.com`
   - **Port**: `6543` (pooler) or `5432` (direct)
   - **Database**: `postgres`
   - **User**: `postgres`
   - **Password**: Your database password

3. For the `.env` file, the connection string format is:
   ```
   postgresql://postgres:[password]@[project-id].pooler.supabase.com:6543/postgres
   ```

### Step 3: Update Your `.env` File

Update `Backend/.env` with your Supabase credentials:

```env
# Supabase Database Configuration
SUPABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@[YOUR_PROJECT_ID].pooler.supabase.com:6543/postgres

# Existing LiteLLM Configuration
LITELLM_PROXY_URL=https://litellm.amzur.com
LITELLM_API_KEY=sk-YLmZIK6subdXeSdRWnyCXg
LLM_MODEL=gpt-4o
LITELLM_EMBEDDING_MODEL=text-embedding-3-large
LITELLM_USER_ID=suma.rudraraju@stackyon.com
IMAGE_GEN_MODEL=gemini/imagen-4.0-fast-generate-001
```

## Running the Schema

### Method 1: Using Supabase Web Console (Recommended for First Time)

1. Go to **SQL Editor** in Supabase Console
2. Click **New Query**
3. Copy the entire contents of `Backend/database/schema.sql`
4. Paste it into the query editor
5. Click **Run**
6. Wait for all tables to be created (should show success messages)

### Method 2: Using Python Script

Create `Backend/scripts/init_db.py`:

```python
import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import db_manager, init_db

async def main():
    """Initialize database from SQL schema"""
    try:
        # Test connection
        if not await db_manager.test_connection():
            print("❌ Failed to connect to database")
            return
        
        print("✅ Database connection successful")
        
        # Read and execute schema
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        engine = await db_manager.get_async_engine()
        async with engine.begin() as conn:
            # Execute schema
            for statement in schema.split(';'):
                statement = statement.strip()
                if statement:
                    try:
                        await conn.execute(statement)
                        print(f"✅ Executed: {statement[:60]}...")
                    except Exception as e:
                        print(f"⚠️  Statement error: {e}")
        
        print("✅ Schema initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
cd Backend
python scripts/init_db.py
```

### Method 3: Using SQLAlchemy ORM

```python
import asyncio
from app.database.models import Base
from app.database.connection import db_manager

async def init_db():
    """Create tables using SQLAlchemy ORM"""
    await db_manager.create_tables()
    print("Tables created successfully!")

asyncio.run(init_db())
```

## Environment Configuration

### Update `Backend/app/settings.py`:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    api_title: str = "Amzur AI Chat API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # LiteLLM Configuration
    litellm_proxy_url: str
    litellm_api_key: str
    llm_model: str = "gpt-4o"
    litellm_embedding_model: Optional[str] = None
    litellm_user_id: Optional[str] = None
    image_gen_model: Optional[str] = None
    
    # Database Configuration
    supabase_url: str
    database_echo: bool = False
    database_pool_size: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Using the ORM Models

### Example 1: Create a User

```python
from app.database.models import User, UserProfile
from app.database.connection import db_manager

async def create_user(email: str, username: str, password_hash: str):
    session = await db_manager.get_async_session()
    try:
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        await session.commit()
        return user
    finally:
        await session.close()
```

### Example 2: Create a Conversation

```python
from app.database.models import Conversation, Message
from uuid import UUID

async def create_conversation(user_id: UUID, title: str):
    session = await db_manager.get_async_session()
    try:
        conversation = Conversation(
            user_id=user_id,
            title=title,
            model_name="gpt-4o",
            status="active"
        )
        session.add(conversation)
        await session.commit()
        return conversation
    finally:
        await session.close()
```

### Example 3: Add a Message

```python
async def add_message(
    conversation_id: UUID,
    user_id: UUID,
    role: str,
    content: str,
    tokens_used: int = None
):
    session = await db_manager.get_async_session()
    try:
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,  # 'user', 'assistant', 'system'
            content=content,
            tokens_used=tokens_used
        )
        session.add(message)
        await session.commit()
        return message
    finally:
        await session.close()
```

## Integration with FastAPI

### Update `Backend/app/main.py`:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.connection import init_db, close_db, get_async_db
from app.routers import chat

# Create lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(
    title="Amzur AI Chat API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/health")
async def health_check(db = Depends(get_async_db)):
    return {"status": "healthy", "database": "connected"}
```

### Create `Backend/app/routers/users.py`:

```python
from fastapi import APIRouter, Depends
from app.database.connection import get_async_db
from app.database.models import User
from app.schemas.user import UserCreate, UserResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    # Hash password
    password_hash = hash_password(user_data.password)
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_async_db)):
    user = await db.get(User, user_id)
    return user
```

## Database Operations

### Query Examples

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Get user by email
async def get_user_by_email(email: str, session: AsyncSession):
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

# Get all conversations for user
async def get_user_conversations(user_id: UUID, session: AsyncSession):
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# Get messages in conversation
async def get_conversation_messages(conversation_id: UUID, session: AsyncSession):
    stmt = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.deleted_at == None
    ).order_by(Message.created_at)
    result = await session.execute(stmt)
    return result.scalars().all()
```

## Security & Row Level Security

### Setting RLS User Context in FastAPI

```python
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

async def set_rls_user(session: AsyncSession, user_id: str):
    """Set RLS user context for the session"""
    await session.execute(f"SET app.user_id = '{user_id}'")

# In your route handlers:
@router.get("/my-conversations")
async def my_conversations(user_id: str, db: AsyncSession = Depends(get_async_db)):
    await set_rls_user(db, user_id)
    # Now queries respect RLS policies
    stmt = select(Conversation)
    result = await db.execute(stmt)
    return result.scalars().all()
```

## Troubleshooting

### Connection Issues

**Error**: `could not translate host name`
- **Solution**: Check your `.env` file for correct hostname format
- Ensure you're using the pooler URL for production

**Error**: `password authentication failed`
- **Solution**: Verify your database password in `.env`
- Reset password in Supabase Console if needed

### Schema Issues

**Error**: `table already exists`
- **Solution**: Run `DROP TABLE IF EXISTS table_name CASCADE;` first
- Or use the web console to drop tables manually

**Error**: `permission denied`
- **Solution**: Ensure your Supabase user has proper permissions
- Contact Supabase support for role/permission issues

### Performance Issues

**Problem**: Slow queries
- **Solution**: 
  - Add indexes (already included in schema)
  - Use connection pooling (configured in `connection.py`)
  - Optimize ORM queries with `selectinload()` for relationships

**Problem**: Connection pool exhaustion
- **Solution**: 
  - Increase `pool_size` in `connection.py`
  - Ensure all sessions are properly closed

### Testing Connection

```bash
# Test from Python
python -c "
import asyncio
from app.database.connection import db_manager

async def test():
    result = await db_manager.test_connection()
    print('Connection: GOOD' if result else 'Connection: FAILED')

asyncio.run(test())
"
```

## Next Steps

1. ✅ Set up Supabase project
2. ✅ Run the schema SQL
3. ✅ Update `.env` with credentials
4. ✅ Integrate models with FastAPI routes
5. Create user authentication endpoints
6. Create chat conversation endpoints
7. Implement analytics tracking
8. Add message feedback collection

## Monitoring & Maintenance

### Check Table Status

In Supabase Console → SQL Editor:
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check row counts
SELECT 
    schemaname,
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

### Regular Backups

Supabase automatically creates daily backups. You can also:
1. Go to **Project Settings** → **Backups**
2. Create manual backups before major changes

## Support

- Supabase Docs: https://supabase.com/docs
- PostgreSQL Docs: https://www.postgresql.org/docs/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/
