"""
Database connection and session management for Supabase PostgreSQL
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    supabase_url: str
    supabase_user: str = "postgres"
    supabase_password: str
    supabase_db: str = "postgres"
    supabase_port: int = 5432
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL from Supabase credentials"""
        # Extract host from Supabase URL
        # Format: postgresql://user:password@host:port/database
        return (
            f"postgresql://{self.supabase_user}:{self.supabase_password}"
            f"@{self.supabase_url}:{self.supabase_port}/{self.supabase_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Build async PostgreSQL connection URL"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


# Global database settings
db_settings = DatabaseSettings()


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None

    @property
    def engine(self) -> Engine:
        """Get or create synchronous SQLAlchemy engine"""
        if self._engine is None:
            self._engine = create_engine(
                self.settings.database_url,
                echo=self.settings.echo_sql,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_pre_ping=self.settings.pool_pre_ping,
                pool_recycle=self.settings.pool_recycle,
                connect_args={"connect_timeout": 10},
            )
            self._setup_engine_listeners(self._engine)
        return self._engine

    async def get_async_engine(self):
        """Get or create asynchronous SQLAlchemy engine"""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.settings.async_database_url,
                echo=self.settings.echo_sql,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_pre_ping=self.settings.pool_pre_ping,
                pool_recycle=self.settings.pool_recycle,
                connect_args={"timeout": 10, "command_timeout": 10},
            )
        return self._async_engine

    def get_session_factory(self):
        """Get or create synchronous session factory"""
        if self._session_factory is None:
            from sqlalchemy.orm import sessionmaker
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    async def get_async_session_factory(self):
        """Get or create asynchronous session factory"""
        if self._async_session_factory is None:
            engine = await self.get_async_engine()
            self._async_session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._async_session_factory

    def get_session(self):
        """Get a new synchronous database session"""
        SessionLocal = self.get_session_factory()
        return SessionLocal()

    async def get_async_session(self) -> AsyncSession:
        """Get a new asynchronous database session"""
        factory = await self.get_async_session_factory()
        return factory()

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            engine = await self.get_async_engine()
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    async def create_tables(self):
        """Create all database tables"""
        try:
            from app.database.models import Base
            engine = await self.get_async_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    async def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            from app.database.models import Base
            engine = await self.get_async_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.warning("Database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {str(e)}")
            raise

    def _setup_engine_listeners(self, engine: Engine):
        """Setup engine event listeners for better logging"""
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Database connection established")

        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")

        @event.listens_for(engine, "close")
        def receive_close(dbapi_conn, connection_record):
            logger.debug("Database connection closed")

    async def close(self):
        """Close all database connections"""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            logger.info("Async engine disposed")

        if self._engine is not None:
            self._engine.dispose()
            logger.info("Sync engine disposed")


# Create a global database manager instance
db_manager = DatabaseManager(db_settings)


# Dependency injection for FastAPI
async def get_async_db() -> Generator[AsyncSession, None, None]:
    """Dependency for getting async database session in FastAPI routes"""
    session = await db_manager.get_async_session()
    try:
        yield session
    finally:
        await session.close()


def get_db() -> Generator:
    """Dependency for getting synchronous database session in FastAPI routes"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


# Startup and shutdown events
async def init_db():
    """Initialize database on application startup"""
    logger.info("Initializing database...")
    if await db_manager.test_connection():
        logger.info("Database connection verified")
    else:
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")


async def close_db():
    """Close database connections on application shutdown"""
    logger.info("Closing database connections...")
    await db_manager.close()
