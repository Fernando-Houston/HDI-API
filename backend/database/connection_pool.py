"""Database connection pooling for better performance"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from contextlib import contextmanager
from typing import Optional
import structlog
import threading
import urllib.parse

logger = structlog.get_logger(__name__)

class DatabasePool:
    """Thread-safe connection pool for PostgreSQL"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            # Use Google Cloud SQL database with proper URL encoding
            db_url = os.getenv('DATABASE_URL')
            
            if db_url:
                # If DATABASE_URL is provided, use it directly
                self.db_url = db_url
            else:
                # Build URL with proper encoding
                password = urllib.parse.quote("JN#Fly/{;>p.bXVL")
                self.db_url = f"postgresql://postgres:{password}@34.135.126.23:5432/hcad"
            
            # Create connection pool
            try:
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,      # Minimum connections
                    maxconn=20,     # Maximum connections
                    dsn=self.db_url,
                    cursor_factory=RealDictCursor
                )
                logger.info("Database connection pool created", 
                           min_connections=2, 
                           max_connections=20)
            except Exception as e:
                logger.error(f"Failed to create connection pool: {str(e)}")
                raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor with automatic connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = None) -> Optional[dict]:
        """Execute a query and return single result"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def close_all(self):
        """Close all connections in the pool"""
        if hasattr(self, '_pool'):
            self._pool.closeall()
            logger.info("All database connections closed")
    
    def get_pool_status(self) -> dict:
        """Get current pool status"""
        if hasattr(self, '_pool'):
            return {
                'min_connections': self._pool.minconn,
                'max_connections': self._pool.maxconn,
                'closed': self._pool.closed
            }
        return {'status': 'not initialized'}

# Global pool instance
db_pool = DatabasePool()

# Convenience functions
def get_connection():
    """Get a database connection from the pool"""
    return db_pool.get_connection()

def get_cursor():
    """Get a database cursor from the pool"""
    return db_pool.get_cursor()

def execute_query(query: str, params: tuple = None) -> list:
    """Execute a query using the pool"""
    return db_pool.execute_query(query, params)

def execute_one(query: str, params: tuple = None) -> Optional[dict]:
    """Execute a query and return one result using the pool"""
    return db_pool.execute_one(query, params)