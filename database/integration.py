#!/usr/bin/env python
"""
Integration module for the Supportly application.
This module registers the products tool with the main Supportly application.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, List, Optional

from .products_tool import ProductsTool, get_tool_description

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductsToolIntegration:
    """
    Integration class for the products tool.
    Manages the lifecycle of the products tool and its registration with the application.
    """
    
    def __init__(self):
        """Initialize the integration."""
        self.tool = ProductsTool()
        self.tool_description = get_tool_description()
        logger.info("ProductsToolIntegration initialized")
    
    async def register_with_app(self, register_tool_fn: Callable[[Dict, Callable], Any]) -> None:
        """
        Register the products tool with the application.
        
        Args:
            register_tool_fn: Function to register the tool with the application
        """
        # Define the executor function that will be called by the application
        async def tool_executor(params: Dict) -> Dict:
            """
            Execute the products tool with the given parameters.
            
            Args:
                params: Parameters for the tool execution
                
            Returns:
                Result of the tool execution
            """
            action = params.get('action')
            if not action:
                return {
                    "error": "No action specified",
                    "response": "I need to know what action to perform with the products tool. Please specify an action."
                }
            
            # Execute the tool with the provided parameters
            result = await self.tool.execute(action, **params)
            return result
        
        # Register the tool with the application
        register_tool_fn(self.tool_description, tool_executor)
        logger.info("Products tool registered with the application")
    
    @classmethod
    async def setup(cls, app):
        """
        Set up the products tool integration with the application.
        
        Args:
            app: The application to integrate with
        """
        integration = cls()
        
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

# Function to set up the integration with the application
async def setup_products_integration(app) -> ProductsToolIntegration:
    """
    Set up the products tool integration with the application.
    
    Args:
        app: The application to integrate with
        
    Returns:
        The integration instance
    """
    return await ProductsToolIntegration.setup(app) 