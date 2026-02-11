# IP Checker Pro - Database Connection Pooling and ORM Configuration
# ==================================================================

import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from datetime import datetime

from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration constants
DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 20))
DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 30))
DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))
DB_ECHO = os.environ.get('DB_ECHO', 'false').lower() == 'true'

class DatabaseManager:
    """Manages database connections with optimized pooling"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize database connection pool"""
        if not self.database_url:
            logger.warning("No DATABASE_URL configured, skipping database initialization")
            return False
            
        try:
            # Create engine with optimized connection pooling
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=DB_POOL_SIZE,
                max_overflow=DB_MAX_OVERFLOW,
                pool_timeout=DB_POOL_TIMEOUT,
                pool_recycle=DB_POOL_RECYCLE,
                pool_pre_ping=True,  # Verify connections before use
                echo=DB_ECHO,
                connect_args={
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000"
                }
            )
            
            # Add connection event listeners for monitoring
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """SQLite specific optimizations"""
                if 'sqlite' in self.database_url:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA cache_size=1000000")
                    cursor.execute("PRAGMA temp_store=memory")
                    cursor.close()
            
            @event.listens_for(self.engine, "checkout")
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                """Log connection checkout"""
                logger.debug(f"Connection checked out: {id(connection_record)}")
            
            @event.listens_for(self.engine, "checkin")
            def receive_checkin(dbapi_connection, connection_record):
                """Log connection checkin"""
                logger.debug(f"Connection checked in: {id(connection_record)}")
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create session factory
            self.SessionLocal = scoped_session(sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            ))
            
            self._initialized = True
            logger.info(f"Database connection pool initialized: {self.database_url}")
            logger.info(f"Pool size: {DB_POOL_SIZE}, Max overflow: {DB_MAX_OVERFLOW}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator:
        """Context manager for database sessions"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
            
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database connection pool statistics"""
        if not self.engine or not hasattr(self.engine.pool, 'status'):
            return {}
        
        try:
            pool = self.engine.pool
            return {
                'pool_size': pool.size(),
                'checked_out_connections': pool.checkedout(),
                'checked_in_connections': pool.checkedin(),
                'overflow_connections': getattr(pool, 'overflow', 0),
                'max_overflow': DB_MAX_OVERFLOW,
                'pool_timeout': DB_POOL_TIMEOUT,
                'recycle_time': DB_POOL_RECYCLE
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {}

# Global database manager instance
db_manager = DatabaseManager()

def init_database(database_url: Optional[str] = None) -> bool:
    """Initialize the global database manager"""
    db_manager.database_url = database_url or db_manager.database_url
    return db_manager.initialize()

@contextmanager
def get_db_session():
    """Get database session - to be used with initialized database"""
    if not db_manager._initialized:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    with db_manager.get_session() as session:
        yield session

# Fallback database manager for when no database is configured
class MockDatabaseManager:
    """Mock database manager for when no real database is available"""
    
    def __init__(self):
        self._initialized = True
    
    @contextmanager
    def get_session(self):
        """Mock session context manager"""
        class MockSession:
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
            def add(self, obj): pass
            def add_all(self, objs): pass
            def query(self, *args, **kwargs): 
                return MockQuery()
        
        class MockQuery:
            def filter(self, *args): return self
            def filter_by(self, **kwargs): return self
            def order_by(self, *args): return self
            def limit(self, n): return []
            def all(self): return []
            def first(self): return None
            def count(self): return 0
        
        yield MockSession()
    
    def get_stats(self):
        return {
            'status': 'mock_database',
            'message': 'No real database configured'
        }

# Use mock database if real database is not available
if not os.environ.get('DATABASE_URL'):
    db_manager = MockDatabaseManager()

# Example usage:
"""
# Initialize database
if init_database():
    # Use in your application
    with get_db_session() as session:
        # Your database operations here
        user = session.query(User).filter_by(email=email).first()
        
# Get connection pool statistics
stats = db_manager.get_stats()
print(f"Active connections: {stats.get('checked_out_connections', 0)}")
"""