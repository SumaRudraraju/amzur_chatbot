"""
SQLAlchemy ORM models for Amzur AI Chat application
Corresponds to the Supabase PostgreSQL schema
"""

from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text, DateTime, 
    ForeignKey, JSON, DECIMAL, INET, Numeric, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field, EmailStr

Base = declarative_base()


# ============================================================================
# USER MANAGEMENT MODELS
# ============================================================================

class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True, index=True)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    chat_settings = relationship("UserChatSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    api_usage = relationship("APIUsage", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    message_feedback = relationship("MessageFeedback", back_populates="user", cascade="all, delete-orphan")
    conversation_ratings = relationship("ConversationRating", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    """User profile with extended information"""
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    avatar_url = Column(Text)
    bio = Column(Text)
    phone_number = Column(String(20))
    country = Column(String(100))
    timezone = Column(String(50), default="UTC")
    preferences = Column(JSON, default={"theme": "light", "notifications": True})
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="profile")


class Session(Base):
    """User session tracking"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


# ============================================================================
# CONVERSATION MODELS
# ============================================================================

class Conversation(Base):
    """Chat conversation/session"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255))
    description = Column(Text)
    model_name = Column(String(100), default="gpt-4o")
    status = Column(String(50), default="active", index=True)
    archived_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    analytics = relationship("ConversationAnalytics", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    ratings = relationship("ConversationRating", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Chat message"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    role = Column(String(20), nullable=False, index=True)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer)
    metadata = Column(JSON, default={})
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")
    feedback = relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")


class MessageAttachment(Base):
    """Message file attachment"""
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100))
    file_size = Column(Integer)
    file_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    message = relationship("Message", back_populates="attachments")


# ============================================================================
# SETTINGS MODELS
# ============================================================================

class UserChatSettings(Base):
    """User chat model settings and preferences"""
    __tablename__ = "user_chat_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    default_model = Column(String(100), default="gpt-4o")
    temperature = Column(Numeric(3, 2), default=0.7)
    max_tokens = Column(Integer, default=2048)
    top_p = Column(Numeric(3, 2), default=1.0)
    frequency_penalty = Column(Numeric(3, 2), default=0)
    presence_penalty = Column(Numeric(3, 2), default=0)
    auto_save = Column(Boolean, default=True)
    save_conversation_history = Column(Boolean, default=True)
    use_system_prompt = Column(Boolean, default=True)
    custom_system_prompt = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="chat_settings")


# ============================================================================
# ANALYTICS MODELS
# ============================================================================

class APIUsage(Base):
    """API usage tracking"""
    __tablename__ = "api_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), index=True)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    response_time_ms = Column(Integer)
    status_code = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="api_usage")


class ConversationAnalytics(Base):
    """Analytics for a conversation"""
    __tablename__ = "conversation_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_count = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 6), default=0)
    average_response_time_ms = Column(Numeric(10, 2))
    sentiment_overall = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="analytics")


# ============================================================================
# AUDIT & LOGGING MODELS
# ============================================================================

class AuditLog(Base):
    """Audit log for tracking user actions"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    changes = Column(JSON)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class ErrorLog(Base):
    """Error log for tracking application errors"""
    __tablename__ = "error_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    error_type = Column(String(100), index=True)
    error_message = Column(Text)
    stack_trace = Column(Text)
    endpoint = Column(String(255))
    method = Column(String(10))
    status_code = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)


# ============================================================================
# SYSTEM & CONFIGURATION MODELS
# ============================================================================

class SystemConfig(Base):
    """System-wide configuration"""
    __tablename__ = "system_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_key = Column(String(255), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class ModelConfig(Base):
    """AI model configuration"""
    __tablename__ = "model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_name = Column(String(100), unique=True, nullable=False, index=True)
    provider = Column(String(100))
    max_tokens = Column(Integer)
    temperature_range = Column(JSON)
    supported_features = Column(JSON, default=[])
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


# ============================================================================
# FEEDBACK & RATINGS MODELS
# ============================================================================

class MessageFeedback(Base):
    """User feedback on messages"""
    __tablename__ = "message_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, index=True)  # 1-5
    feedback_text = Column(Text)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    message = relationship("Message", back_populates="feedback")
    user = relationship("User", back_populates="message_feedback")


class ConversationRating(Base):
    """User rating for entire conversation"""
    __tablename__ = "conversation_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_rating = Column(Integer)  # 1-5
    quality_rating = Column(Integer)  # 1-5
    relevance_rating = Column(Integer)  # 1-5
    comments = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="ratings")
    user = relationship("User", back_populates="conversation_ratings")


# ============================================================================
# PYDANTIC SCHEMAS FOR API RESPONSES
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    model_name: str = "gpt-4o"


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    conversation_id: str
    tokens_used: Optional[int] = None


class MessageResponse(MessageBase):
    id: str
    conversation_id: str
    user_id: Optional[str] = None
    created_at: datetime
    is_edited: bool

    class Config:
        from_attributes = True


class ChatSettingsResponse(BaseModel):
    default_model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    auto_save: bool
    save_conversation_history: bool
    use_system_prompt: bool

    class Config:
        from_attributes = True
