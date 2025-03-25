"""
Supportly Shoe Store database package.
Provides functionality for interacting with the product database.
"""

from .db_connection import db
from .products_repository import ProductsRepository
from .products_agent import ProductsAgent
from .products_tool import ProductsTool, get_tool_description
from .api import products_router

__all__ = [
    'db',
    'ProductsRepository',
    'ProductsAgent',
    'ProductsTool',
    'get_tool_description',
    'products_router'
] 