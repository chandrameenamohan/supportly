#!/usr/bin/env python
"""
Products Agent module for the Supportly chatbot.
This module integrates with the database to search for products and generate natural language responses.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional, Union, Tuple

from .products_repository import ProductsRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductsAgent:
    """
    Agent that interacts with the product database to provide shopping assistance.
    Parses natural language queries, retrieves product information, and formats responses.
    """
    
    def __init__(self):
        """Initialize the products agent."""
        self.repository = ProductsRepository
        logger.info("Products agent initialized")
    
    async def search_products(self, query: str) -> Dict:
        """
        Search for products based on a natural language query.
        
        Args:
            query: Natural language query from the user
            
        Returns:
            Dictionary with search results and formatted response
        """
        # Extract search parameters from the query
        search_params = self._extract_search_params(query)
        logger.info(f"Extracted search parameters: {search_params}")
        
        # Search the database
        results = await self.repository.search_products(
            query=search_params.get("query"),
            category_id=search_params.get("category_id"),
            brand_id=search_params.get("brand_id"),
            price_min=search_params.get("price_min"),
            price_max=search_params.get("price_max"),
            size=search_params.get("size"),
            color=search_params.get("color"),
            limit=10,
            offset=0
        )
        
        # Format the response
        response = self._format_search_response(results, search_params, query)
        
        return {
            "results": results,
            "response": response
        }
    
    async def get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed information about a product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Dictionary with product details and formatted response
        """
        # Get product details
        product_details = await self.repository.get_product_details_complete(product_id)
        
        # Format the response
        response = self._format_product_details_response(product_details)
        
        return {
            "details": product_details,
            "response": response
        }
    
    async def check_product_availability(self, product_id: str, size: str, color: str) -> Dict:
        """
        Check if a product is available in a specific size and color.
        
        Args:
            product_id: UUID of the product
            size: Size of the product
            color: Color of the product
            
        Returns:
            Dictionary with availability information and formatted response
        """
        # Get product details
        product = await self.repository.get_product_by_id(product_id)
        if not product:
            return {
                "available": False,
                "response": "I'm sorry, I couldn't find that product in our database."
            }
        
        # Check inventory
        inventory = await self.repository.check_inventory(product_id, size, color)
        
        # Format the response
        available = inventory is not None and inventory.get("quantity", 0) > 0
        response = self._format_availability_response(product, inventory, size, color)
        
        return {
            "product": product,
            "inventory": inventory,
            "available": available,
            "response": response
        }
    
    async def get_category_products(self, category_name: str) -> Dict:
        """
        Get products in a specific category.
        
        Args:
            category_name: Name of the category
            
        Returns:
            Dictionary with products and formatted response
        """
        # Get products in category
        products = await self.repository.get_category_products(
            category_name=category_name,
            include_subcategories=True,
            limit=10
        )
        
        # Format the response
        response = self._format_category_products_response(products, category_name)
        
        return {
            "products": products,
            "response": response
        }
    
    def _extract_search_params(self, query: str) -> Dict:
        """
        Extract search parameters from a natural language query.
        Uses regex patterns to identify common search parameters.
        
        Args:
            query: Natural language query
            
        Returns:
            Dictionary of search parameters
        """
        params = {}
        
        # Extract brand
        brand_patterns = [
            r'brand\s*:\s*([a-zA-Z0-9 ]+)',
            r'by\s+([a-zA-Z]+)',
            r'from\s+([a-zA-Z]+)'
        ]
        for pattern in brand_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                brand_name = match.group(1).strip()
                # In a production system, we would look up the brand ID here
                # For now, we'll just pass the name as the query
                params["query"] = brand_name
                break
        
        # Extract price range
        price_range_pattern = r'(?:between|from)\s*\$?(\d+)\s*(?:and|to|-)\s*\$?(\d+)'
        min_price_pattern = r'(?:over|above|more than|min|minimum)\s*\$?(\d+)'
        max_price_pattern = r'(?:under|below|less than|max|maximum)\s*\$?(\d+)'
        color_pattern = r'(?:color|colour)\s*:\s*([a-zA-Z]+)|([a-zA-Z]+)\s+(?:color|colour)s?'
        size_pattern = r'(?:size)\s*:\s*([a-zA-Z0-9.]+)|size\s+([a-zA-Z0-9.]+)'
        
        match = re.search(price_range_pattern, query, re.IGNORECASE)
        if match:
            params["price_min"] = float(match.group(1))
            params["price_max"] = float(match.group(2))
        else:
            # Try to find min or max individually
            min_match = re.search(min_price_pattern, query, re.IGNORECASE)
            if min_match:
                params["price_min"] = float(min_match.group(1))
            
            max_match = re.search(max_price_pattern, query, re.IGNORECASE)
            if max_match:
                params["price_max"] = float(max_match.group(1))
        
        # Extract color
        match = re.search(color_pattern, query, re.IGNORECASE)
        if match:
            color = match.group(1) if match.group(1) else match.group(2)
            params["color"] = color.strip()
        
        # Extract size
        match = re.search(size_pattern, query, re.IGNORECASE)
        if match:
            size = match.group(1) if match.group(1) else match.group(2)
            params["size"] = size.strip()
        
        # If we haven't set a query parameter yet, use the whole query
        if "query" not in params:
            # Remove identified parameters from the query to get a cleaner search term
            clean_query = query
            for param in ["price_min", "price_max", "color", "size"]:
                if param in params:
                    pattern = None
                    if param == "price_min":
                        pattern = min_price_pattern
                    elif param == "price_max":
                        pattern = max_price_pattern
                    elif param == "color":
                        pattern = color_pattern
                    elif param == "size":
                        pattern = size_pattern
                    
                    if pattern:
                        clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE)
            
            # Also remove price range pattern
            clean_query = re.sub(price_range_pattern, '', clean_query, flags=re.IGNORECASE)
            
            # Clean up and set as query
            clean_query = clean_query.strip()
            if clean_query:
                params["query"] = clean_query
        
        return params
    
    def _format_search_response(self, results: List[Dict], params: Dict, original_query: str) -> str:
        """
        Format search results into a natural language response.
        
        Args:
            results: List of product dictionaries
            params: Search parameters used
            original_query: Original query from the user
            
        Returns:
            Formatted response string
        """
        if not results:
            return f"I'm sorry, I couldn't find any products matching '{original_query}'. Could you try a different search?"
        
        # Start with an introduction
        response_parts = [f"Here are some products that match your search for '{original_query}':"]
        
        # Add results
        for i, product in enumerate(results[:5], 1):
            price_display = f"${product.get('sale_price', 0)}" if product.get("is_on_sale") else f"${product.get('price', 0)}"
            
            product_info = f"{i}. **{product.get('name')}** by {product.get('brand_name')} - {price_display}"
            
            # Add rating if available
            if product.get("avg_rating"):
                product_info += f" (Rating: {product.get('avg_rating')}/5)"
                
            response_parts.append(product_info)
        
        # Add a prompt for more details
        if results:
            response_parts.append("\nWould you like more details about any of these products? Or would you like to refine your search?")
        
        return "\n".join(response_parts)
    
    def _format_product_details_response(self, product_details: Dict) -> str:
        """
        Format product details into a natural language response.
        
        Args:
            product_details: Dictionary with product details
            
        Returns:
            Formatted response string
        """
        if "error" in product_details:
            return f"I'm sorry, I couldn't find that product. {product_details.get('error')}"
        
        # Basic product info
        name = product_details.get("name", "Unknown Product")
        brand = product_details.get("brand_name", "Unknown Brand")
        category = product_details.get("category_name", "Unknown Category")
        
        # Price information
        price = product_details.get("price", 0)
        sale_price = product_details.get("sale_price")
        is_on_sale = product_details.get("is_on_sale", False)
        
        price_text = f"${price:.2f}"
        if is_on_sale and sale_price:
            discount = ((price - sale_price) / price) * 100
            price_text = f"${sale_price:.2f} (${price:.2f} - {discount:.0f}% off)"
        
        # Description
        description = product_details.get("description", "No description available.")
        
        # Reviews
        reviews = product_details.get("reviews", {})
        review_count = reviews.get("count", 0)
        avg_rating = reviews.get("average_rating", 0)
        
        # Inventory
        inventory = product_details.get("inventory", [])
        available_sizes = set()
        available_colors = set()
        
        for item in inventory:
            if item.get("quantity", 0) > 0:
                available_sizes.add(item.get("size", ""))
                available_colors.add(item.get("color", ""))
        
        # Format the response
        response_parts = [
            f"# {name}",
            f"**Brand**: {brand} | **Category**: {category}",
            f"**Price**: {price_text}",
            "",
            f"{description}",
            "",
            f"**Rating**: {avg_rating}/5 ({review_count} reviews)"
        ]
        
        # Add available sizes and colors
        if available_sizes:
            response_parts.append(f"**Available Sizes**: {', '.join(sorted(available_sizes))}")
        
        if available_colors:
            response_parts.append(f"**Available Colors**: {', '.join(sorted(available_colors))}")
        
        # Add related products
        related_products = product_details.get("related_products", [])
        if related_products:
            response_parts.append("\n**You might also like**:")
            for i, related in enumerate(related_products[:3], 1):
                related_price = f"${related.get('sale_price')}" if related.get("is_on_sale") else f"${related.get('price')}"
                response_parts.append(f"{i}. {related.get('name')} - {related_price}")
        
        # Add a prompt for more actions
        response_parts.append("\nWhat would you like to know about this product? You can ask about sizes, colors, or reviews.")
        
        return "\n".join(response_parts)
    
    def _format_availability_response(self, product: Dict, inventory: Optional[Dict], size: str, color: str) -> str:
        """
        Format availability information into a natural language response.
        
        Args:
            product: Product dictionary
            inventory: Inventory dictionary
            size: Requested size
            color: Requested color
            
        Returns:
            Formatted response string
        """
        name = product.get("name", "Unknown Product")
        
        if not inventory:
            return f"I'm sorry, the {name} is not available in size {size} and color {color}. Would you like to check other sizes or colors?"
        
        quantity = inventory.get("quantity", 0)
        
        if quantity <= 0:
            return f"I'm sorry, the {name} in size {size} and color {color} is currently out of stock. Would you like to check other sizes or colors?"
        
        if quantity < 5:
            return f"Good news! The {name} is available in size {size} and color {color}, but there are only {quantity} left in stock. Would you like to purchase it?"
        
        return f"Great news! The {name} is available in size {size} and color {color}. Would you like to add it to your cart?"
    
    def _format_category_products_response(self, products: List[Dict], category_name: str) -> str:
        """
        Format category products into a natural language response.
        
        Args:
            products: List of product dictionaries
            category_name: Name of the category
            
        Returns:
            Formatted response string
        """
        if not products:
            return f"I'm sorry, I couldn't find any products in the '{category_name}' category. Would you like to browse a different category?"
        
        # Start with an introduction
        response_parts = [f"Here are some popular products in the '{category_name}' category:"]
        
        # Add results
        for i, product in enumerate(products[:5], 1):
            price_display = f"${product.get('sale_price', 0)}" if product.get("is_on_sale") else f"${product.get('price', 0)}"
            
            product_info = f"{i}. **{product.get('name')}** by {product.get('brand_name')} - {price_display}"
            response_parts.append(product_info)
        
        # Add a prompt for more details
        response_parts.append("\nWould you like more details about any of these products? Or would you like to see more products in this category?")
        
        return "\n".join(response_parts) 