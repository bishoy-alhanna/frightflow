"""
Shared database access layer with SQLAlchemy 2.0 and Alembic support.
"""
import logging
import time
from typing import Optional, Any, Dict
from contextlib import contextmanager
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, OperationalError
import functools

logger = logging.getLogger(__name__)

# Global database instance
db = SQLAlchemy()
migrate = Migrate()


def init_db(app: Flask) -> SQLAlchemy:
    """Initialize database with Flask app."""
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Setup connection event listeners
    setup_connection_events()
    
    return db


def setup_connection_events():
    """Setup SQLAlchemy connection event listeners for monitoring."""
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas if using SQLite."""
        if 'sqlite' in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log slow queries."""
        context._query_start_time = time.time()
    
    @event.listens_for(Engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log query execution time."""
        total = time.time() - context._query_start_time
        if total > 1.0:  # Log queries taking more than 1 second
            logger.warning(f"Slow query: {total:.2f}s - {statement[:100]}...")


def retry_db_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry database operations on connection failures."""
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (DisconnectionError, OperationalError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


@contextmanager
def db_transaction():
    """Context manager for database transactions with automatic rollback on error."""
    try:
        db.session.begin()
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise
    finally:
        db.session.close()


class BaseModel(db.Model):
    """Base model class with common fields and methods."""
    
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
        nullable=False
    )
    
    def to_dict(self, exclude: Optional[list] = None) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        exclude = exclude or []
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if hasattr(value, 'isoformat'):  # Handle datetime objects
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    def update(self, **kwargs):
        """Update model instance with provided kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create(cls, **kwargs):
        """Create and save a new instance."""
        instance = cls(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    def save(self):
        """Save the current instance."""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete the current instance."""
        db.session.delete(self)
        db.session.commit()


class PaginationHelper:
    """Helper class for pagination."""
    
    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 20, max_per_page: int = 100):
        """Paginate a SQLAlchemy query."""
        per_page = min(per_page, max_per_page)
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            'items': [item.to_dict() if hasattr(item, 'to_dict') else item for item in pagination.items],
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        }


@retry_db_operation(max_retries=3)
def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def create_tables():
    """Create all database tables."""
    db.create_all()


def drop_tables():
    """Drop all database tables."""
    db.drop_all()


def reset_database():
    """Reset database by dropping and recreating all tables."""
    drop_tables()
    create_tables()

