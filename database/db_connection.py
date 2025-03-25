#!/usr/bin/env python
"""
Database connection module for the Supportly product database.
This module handles PostgreSQL connections and query execution.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
import asyncpg
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default connection parameters
DEFAULT_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "supportly_shoes"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

class DatabaseConnection:
    """
    Manages database connections and query execution for the products database.
    Uses connection pooling for efficient database access.
    """
    
    _pool = None
    
    @classmethod
    async def get_pool(cls, config: Optional[Dict] = None) -> asyncpg.Pool:
        """
        Get or create a connection pool.
        
        Args:
            config: Optional database configuration override
            
        Returns:
            Connection pool
        """
        if cls._pool is None:
            try:
                # Use provided config or default
                db_config = config or DEFAULT_DB_CONFIG
                cls._pool = await asyncpg.create_pool(**db_config)
                logger.info(f"Connected to database {db_config['database']} on {db_config['host']}")
            except Exception as e:
                logger.error(f"Error creating database pool: {str(e)}")
                raise
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """Close the connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    async def execute_query(cls, query: str, *args) -> List[Dict]:
        """
        Execute a query and return the results as a list of dictionaries.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of dictionaries with query results
        """
        pool = await cls.get_pool()
        try:
            async with pool.acquire() as conn:
                # Execute the query
                stmt = await conn.prepare(query)
                rows = await stmt.fetch(*args)
                
                # Convert to dictionaries
                result = [dict(row) for row in rows]
                return result
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            raise
    
    @classmethod
    async def execute_transaction(cls, *queries_and_args) -> List[List[Dict]]:
        """
        Execute multiple queries in a transaction.
        
        Args:
            *queries_and_args: Tuples of (query, args)
            
        Returns:
            List of results for each query
        """
        pool = await cls.get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    results = []
                    for query_and_args in queries_and_args:
                        query = query_and_args[0]
                        args = query_and_args[1] if len(query_and_args) > 1 else []
                        
                        stmt = await conn.prepare(query)
                        rows = await stmt.fetch(*args)
                        result = [dict(row) for row in rows]
                        results.append(result)
                    return results
        except Exception as e:
            logger.error(f"Error executing transaction: {str(e)}")
            raise

# Singleton instance for easy import
db = DatabaseConnection 