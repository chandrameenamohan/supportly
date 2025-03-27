#!/usr/bin/env python3
"""
Database initialization script for the SQLAlchemy database defined in message_logger.py.
This script creates all the tables defined in the database models.
"""
from dotenv import load_dotenv
import sys, os
import asyncio
from message_logger import get_message_logger
from order_data import get_orders_db

load_dotenv()
DB_URL = os.getenv("DB_URL") or "sqlite+aiosqlite:///db.sqlite"

async def initialize_database():
    """
    Initialize the database by creating all tables.
    """
    logger = get_message_logger(DB_URL)
    await logger.initialize()
    orders_db = await get_orders_db(DB_URL)
    await orders_db.initialize()

async def main():
    try:
        await initialize_database()
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
