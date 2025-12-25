"""
Database connection and session management.
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager
from config import get_settings
import structlog
import time

settings = get_settings()
logger = structlog.get_logger()

# Connection pool configuration
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600  # Recycle connections after 1 hour

# Create engine with connection pooling and retry logic
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    echo=settings.log_level == "DEBUG",
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    }
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_connection_with_retry(max_retries: int = 3, delay: float = 1.0):
    """Attempt to create a database connection with retries."""
    last_error = None
    for attempt in range(max_retries):
        try:
            conn = engine.connect()
            conn.execute(text("SELECT 1"))
            conn.close()
            return True
        except OperationalError as e:
            last_error = e
            logger.warning(
                "database_connection_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
    
    logger.error("database_connection_failed", error=str(last_error))
    return False


@contextmanager
def get_db() -> Session:
    """Database session context manager with error handling."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except OperationalError as e:
        db.rollback()
        logger.error("database_operation_error", error=str(e))
        raise
    except Exception as e:
        db.rollback()
        logger.error("database_error", error=str(e))
        raise
    finally:
        db.close()


def check_db_health() -> dict:
    """Check database connection health."""
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def init_db():
    """Initialize database tables."""
    # First, ensure we can connect
    if not _create_connection_with_retry():
        logger.error("init_db_failed", message="Could not establish database connection")
        raise RuntimeError("Failed to connect to database during initialization")
    
    from models.database import Base
    from models.crew_models import (
        CrewSession, AgentMessage, CrewVote, CrewPerformance
    )
    from models.economic_event import EconomicEvent
    # Import all models to ensure they're registered
    Base.metadata.create_all(bind=engine)
    logger.info("database_initialized", message="Database tables created (including crew and economic event models)")
    print("✓ Database tables created (including crew and economic event models)")


# Log connection pool events for monitoring
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("db_connection_checkout", 
                pool_size=engine.pool.size(),
                checkedout=engine.pool.checkedout())


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool."""
    logger.debug("db_connection_checkin",
                pool_size=engine.pool.size(),
                checkedout=engine.pool.checkedout())
