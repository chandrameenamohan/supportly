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
from .products_repository import ProductsRepository
from .db_connection import IN_MEMORY_DB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_tool_description():
    """
    Get a description of the products tool for LLM context.
    This provides the LLM with information about the tool's capabilities.
    
    Returns:
        String description of the tool
    """
    return """
    ProductsTool: A tool for querying product information.
    
    This tool can:
    - Search for products using natural language queries
    - Provide detailed information about specific products
    - Check product availability by size and color
    - Browse products by category
    - Show popular and featured products
    
    The tool handles natural language processing to understand user queries and return formatted responses.
    """

class ProductsTool:
    """
    Tool that allows the chatbot to access product information.
    Provides methods for the LLM to query the product database through the products agent.
    """

    def __init__(self):
        """Initialize the products tool."""
        self.agent = ProductsAgent()
        # Initialize the vector database on tool creation
        asyncio.create_task(self._initialize_vector_db())
        logger.info("Products tool initialized")
    
    async def _initialize_vector_db(self):
        """Initialize the vector database and index products."""
        try:
            # Initialize vector database
            success = await ProductsRepository.initialize_vector_db()
            if success:
                logger.info("Vector database initialized successfully")
            else:
                logger.error("Failed to initialize vector database")
        except Exception as e:
            logger.error(f"Error initializing vector database: {str(e)}")
    
    async def execute(self, action: str, **kwargs) -> Dict:
        """
        Execute a product-related action.
        
        Args:
            action: The action to execute (search, details, availability, category, popular)
            **kwargs: Additional arguments for the action
            
        Returns:
            A dictionary with the result and a formatted response
        """
        try:
            # Log the inputs for debugging
            logger.info(f"Product tool executing action: {action} with params: {kwargs}")
            
            # Handle the case where product_id might be in query
            if action == "availability" and "product_id" in kwargs and "query" in kwargs:
                # Extract product info from query if product_id is not specific enough
                query = kwargs.get("query", "")
                if query and (kwargs["product_id"] is None or kwargs["product_id"] == ""):
                    # Try to extract product ID from query
                    try:
                        # Use simple extraction - a more robust approach would use LLM
                        product_matches = []
                        for product in self.agent.repository.IN_MEMORY_DB["products"]:
                            if product["name"].lower() in query.lower():
                                product_matches.append(product["id"])
                        
                        if product_matches:
                            kwargs["product_id"] = product_matches[0]
                            logger.info(f"Extracted product_id {kwargs['product_id']} from query")
                    except Exception as e:
                        logger.error(f"Error extracting product_id from query: {str(e)}")
            
            # Route to appropriate method
            if action == "search":
                return await self._search_products(**kwargs)
            elif action == "details":
                return await self._get_product_details(**kwargs)
            elif action == "availability":
                # Ensure we pass the original query for context
                original_query = kwargs.get("query", "")
                # Remove query from kwargs to avoid unexpected parameter errors when not handled
                availability_params = {k: v for k, v in kwargs.items() if k != "query"}
                # Add query as a properly named parameter
                return await self._check_availability(query=original_query, **availability_params)
            elif action == "category":
                return await self._get_category_products(**kwargs)
            elif action == "popular":
                return await self._get_popular_products()
            else:
                # Log unknown action
                logger.warning(f"Unknown product tool action requested: {action}")
                return {
                    "error": f"Unknown action: {action}",
                    "response": f"I'm sorry, I don't know how to perform the action '{action}' for products. Would you like to see our popular products instead?"
                }
        except Exception as e:
            logger.error(f"Error executing product tool action '{action}': {str(e)}", exc_info=True)
            # Provide a more helpful error response
            error_response = f"I encountered an error while trying to get product information. "
            
            if "product_id" in kwargs and kwargs["product_id"]:
                error_response += f"I couldn't find information about the product '{kwargs['product_id']}'. "
            
            error_response += "Would you like to see our popular products instead?"
            
            return {
                "error": str(e),
                "response": error_response
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

    async def _get_product_details(self, product_id: Optional[str] = None) -> Dict:
        """
        Get details for a specific product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Dictionary with product details and formatted response
        """
        # If no product ID is provided, show popular products instead
        if not product_id:
            logger.info("No product_id provided for details action, showing popular products instead")
            return await self._get_popular_products()
        
        # Get product details
        return await self.agent.get_product_details(product_id)
    
    async def _get_popular_products(self) -> Dict:
        """
        Get a list of popular products.
        
        Returns:
            Dictionary with popular products and formatted response
        """
        return await self.agent.get_popular_products()
    
    async def _check_availability(self, product_id: Optional[str] = None, size: Optional[str] = None, color: Optional[str] = None, query: Optional[str] = None) -> Dict:
        """
        Check if a product is available in a specific size and color.
        
        Args:
            product_id: UUID or name of the product
            size: Size of the product (optional)
            color: Color of the product (optional)
            query: Original query string for context extraction (optional)
            
        Returns:
            Dictionary with availability information and formatted response
        """
        # Handle missing product_id in follow-up queries
        if not product_id:
            # Try to extract product from query if available
            extracted_product = None
            if query:
                for product in IN_MEMORY_DB["products"]:
                    if product["name"].lower() in query.lower():
                        extracted_product = product["id"]
                        logger.info(f"Extracted product_id {extracted_product} from query: '{query}'")
                        break
            
            if extracted_product:
                product_id = extracted_product
            else:
                return {
                    "error": "No product specified for availability check",
                    "response": "I'm not sure which product you're asking about. Could you specify which shoe you'd like to check for availability? For example, 'Do you have Nike Air Max in size 10?'"
                }
        
        # Handle case where product_id is a name, not an ID
        actual_product_id = product_id
        if not any(p["id"] == product_id for p in IN_MEMORY_DB["products"]):
            # Try to find the product by name (case insensitive)
            product_name_lower = product_id.lower()
            found = False
            for product in IN_MEMORY_DB["products"]:
                if product_name_lower in product["name"].lower():
                    actual_product_id = product["id"]
                    found = True
                    logger.info(f"Found product ID {actual_product_id} for name '{product_id}'")
                    break
            
            if not found:
                return {
                    "error": "Product not found",
                    "response": f"I'm sorry, I couldn't find any product matching '{product_id}' in our database."
                }
        
        # Get product details first
        product_details = await self.agent.get_product_details(actual_product_id)
        product = product_details.get("details", {})
        
        if not product:
            return {
                "error": "Product not found",
                "response": f"I'm sorry, I couldn't find that product in our database."
            }
        
        # If size and color aren't provided, return general availability information
        if not size or not color:
            # Extract available sizes and colors from attributes
            sizes = product.get("attributes", {}).get("sizes", [])
            colors = product.get("attributes", {}).get("color", [])
            
            sizes_text = "Sizes: " + (", ".join(sizes) if sizes else "Not specified")
            colors_text = "Colors: " + (", ".join(colors) if colors else "Not specified")
            
            return {
                "product": product,
                "response": f"The {product.get('name')} is available in the following sizes and colors: \n{sizes_text} \n{colors_text}"
            }
        
        # If size and color are provided, check specific availability
        return await self.agent.check_product_availability(actual_product_id, size, color)
    
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