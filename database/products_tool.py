#!/usr/bin/env python
"""
Products Tool module for the Supportly Chatbot.
This module provides a tool for the LLM-based chatbot to query the product database.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple

from .products_agent import ProductsAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductsTool:
    """
    Tool that allows the chatbot to access product information.
    Provides methods for the LLM to query the product database through the products agent.
    """

    def __init__(self):
        """Initialize the products tool."""
        self.agent = ProductsAgent()
        logger.info("Products tool initialized")
    
    async def execute(self, action: str, **kwargs) -> Dict:
        """
        Execute a product-related action.
        
        Args:
            action: The action to execute (search, details, availability, category)
            **kwargs: Additional arguments for the action
            
        Returns:
            A dictionary with the result and a formatted response
        """
        try:
            if action == "search":
                return await self._search_products(**kwargs)
            elif action == "details":
                return await self._get_product_details(**kwargs)
            elif action == "availability":
                return await self._check_availability(**kwargs)
            elif action == "category":
                return await self._get_category_products(**kwargs)
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "response": f"I'm sorry, I don't know how to perform the action '{action}' for products."
                }
        except Exception as e:
            logger.error(f"Error executing product tool action '{action}': {str(e)}")
            return {
                "error": str(e),
                "response": f"I encountered an error while trying to get product information: {str(e)}"
            }

    async def _search_products(self, query: str) -> Dict:
        """
        Search for products based on a natural language query.
        
        Args:
            query: Natural language query from the user
            
        Returns:
            Dictionary with search results and formatted response
        """
        if not query:
            return {
                "error": "No query provided",
                "response": "I need to know what kind of shoes you're looking for. Could you provide more details?"
            }
        
        return await self.agent.search_products(query)

    async def _get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed information about a product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Dictionary with product details and formatted response
        """
        if not product_id:
            return {
                "error": "No product ID provided",
                "response": "I need a product ID to provide detailed information. Could you specify which product you're interested in?"
            }
        
        return await self.agent.get_product_details(product_id)
    
    async def _check_availability(self, product_id: str, size: str, color: str) -> Dict:
        """
        Check if a product is available in a specific size and color.
        
        Args:
            product_id: UUID of the product
            size: Size of the product
            color: Color of the product
            
        Returns:
            Dictionary with availability information and formatted response
        """
        if not product_id:
            return {
                "error": "No product ID provided",
                "response": "I need a product ID to check availability. Could you specify which product you're interested in?"
            }
        
        if not size:
            return {
                "error": "No size provided",
                "response": "I need to know which size you're looking for. Could you specify a size?"
            }
        
        if not color:
            return {
                "error": "No color provided",
                "response": "I need to know which color you're looking for. Could you specify a color?"
            }
        
        return await self.agent.check_product_availability(product_id, size, color)
    
    async def _get_category_products(self, category_name: str) -> Dict:
        """
        Get products in a specific category.
        
        Args:
            category_name: Name of the category
            
        Returns:
            Dictionary with products and formatted response
        """
        if not category_name:
            return {
                "error": "No category name provided",
                "response": "I need to know which category you're interested in. We have categories like Running, Basketball, Casual, and more. Which would you like to explore?"
            }
        
        return await self.agent.get_category_products(category_name)

# Function to create a serializable description of the tool for the LLM
def get_tool_description() -> Dict:
    """
    Get a description of the products tool for the LLM.
    
    Returns:
        A dictionary describing the tool's capabilities
    """
    return {
        "name": "products_tool",
        "description": "Use this tool to search for shoes and get product information from our database.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "details", "availability", "category"],
                    "description": "The action to perform with the products tool."
                },
                "query": {
                    "type": "string",
                    "description": "For search action: Natural language query to search for products."
                },
                "product_id": {
                    "type": "string",
                    "description": "For details and availability actions: UUID of the product."
                },
                "size": {
                    "type": "string",
                    "description": "For availability action: Size of the product."
                },
                "color": {
                    "type": "string",
                    "description": "For availability action: Color of the product."
                },
                "category_name": {
                    "type": "string",
                    "description": "For category action: Name of the category to get products from."
                }
            },
            "required": ["action"]
        }
    } 