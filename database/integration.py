#!/usr/bin/env python
"""
Integration module for the products database.
This module provides functionality to integrate the products agent and tool with the main application.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

from .products_tool import ProductsTool
from .products_repository import ProductsRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductsToolIntegration:
    """
    Integration class for the products tool.
    Provides functionality to register the tool with the main application.
    """
    
    def __init__(self):
        """Initialize the products tool integration."""
        self.tool = ProductsTool()
        logger.info("Products tool integration initialized")
    
    async def register_with_app(self, register_tool_func: Callable):
        """
        Register the products tool with the application.
        
        Args:
            register_tool_func: Function to register the tool with the application
        """
        from .products_tool import get_tool_description
        
        # Register the tool
        await register_tool_func(
            "products",
            self.tool.execute,
            get_tool_description()
        )
        
        logger.info("Products tool registered with the application")
    
    @classmethod
    async def setup(cls, app):
        """
        Set up the products tool integration with the application.
        
        Args:
            app: The application to integrate with
        """
        integration = cls()
        
        # Initialize vector database
        asyncio.create_task(cls._initialize_vector_database())
        
        # Check if the application has a register_tool method
        if hasattr(app, 'register_tool'):
            await integration.register_with_app(app.register_tool)
        else:
            logger.error("Application does not have a register_tool method")
        
        # Check if the application has a FastAPI instance to register routes with
        if hasattr(app, 'api') and hasattr(app.api, 'include_router'):
            from .api import products_router
            app.api.include_router(products_router)
            logger.info("Products API routes registered with the application")
        elif hasattr(app, 'include_router'):
            from .api import products_router
            app.include_router(products_router)
            logger.info("Products API routes registered with the application")
        else:
            logger.warning("Could not register API routes: No FastAPI instance found")
        
        return integration
    
    @classmethod
    async def _initialize_vector_database(cls):
        """Initialize the vector database."""
        try:
            # Initialize vector database
            success = await ProductsRepository.initialize_vector_db()
            if success:
                logger.info("Vector database initialized during application startup")
            else:
                logger.error("Failed to initialize vector database during application startup")
        except Exception as e:
            logger.error(f"Error initializing vector database during application startup: {str(e)}")

# Public function to set up products integration with the application
async def setup_products_integration(app=None):
    """
    Set up the products integration with the application.
    
    Args:
        app: The application to integrate with
        
    Returns:
        ProductsToolIntegration instance
    """
    return await ProductsToolIntegration.setup(app) 