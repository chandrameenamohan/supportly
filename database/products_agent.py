#!/usr/bin/env python
"""
Products Agent module for the Supportly chatbot.
This module integrates with the database to search for products and generate natural language responses.
"""

import asyncio
import logging
import json
import re
import os
from typing import Dict, List, Any, Optional, Union, Tuple

from .products_repository import ProductsRepository, get_vector_db
from .db_connection import IN_MEMORY_DB

# Try to import OpenAI for parameter extraction
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
        self.openai_client = None
        if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            self.openai_client = OpenAI()
        logger.info("Products agent initialized")
    
    async def search_products(self, query: str) -> Dict:
        """
        Search for products based on natural language query.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary with search results and formatted response
        """
        logger.info(f"Processing search query: {query}")
        
        # Extract search parameters from query using LLM if available
        params = await self._extract_search_parameters(query)
        
        # Check if vector db is available before trying semantic search
        vector_db = get_vector_db()
        if vector_db and query and await self._is_vector_search_available():
            logger.info("Attempting semantic search...")
            # Use semantic search for better results
            products = await self.repository.semantic_search_products(
                query=query,
                filters=params.get("filters", {}),
                limit=10
            )
        else:
            products = []
            logger.info("Vector search not available or disabled. Skipping semantic search.")
            
        # If semantic search returned no results or was skipped, fall back to standard search
        if not products:
            logger.info("Falling back to standard search.")
            
            # Convert parameters to the format expected by search_products
            category_id = None
            brand_id = None
            price_min = params.get("price_min")
            price_max = params.get("price_max")
            size = params.get("size")
            color = params.get("color")
            
            # Get category ID if category name is specified
            if params.get("category"):
                category_name = params["category"].lower()
                for category in IN_MEMORY_DB["categories"]:
                    if category["name"].lower() == category_name:
                        category_id = category["id"]
                        break
            
            # Get brand ID if brand name is specified
            if params.get("brand"):
                brand_name = params["brand"].lower()
                for brand in IN_MEMORY_DB["brands"]:
                    if brand["name"].lower() == brand_name:
                        brand_id = brand["id"]
                        break
            
            # Perform standard search
            products = await self.repository.search_products(
                query=query,
                category_id=category_id,
                brand_id=brand_id,
                price_min=price_min,
                price_max=price_max,
                size=size,
                color=color,
                limit=params.get("limit", 10),
                offset=0,
                use_semantic_search=False
            )
        
        # Sort the results if a specific sort order was requested
        if params.get("sort") == "price-desc":
            products.sort(key=lambda p: -(p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]))
        elif params.get("sort") == "price-asc":
            products.sort(key=lambda p: (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]))
        
        # Format the response
        response = self._format_search_results(products, query)
        
        return {
            "results": products,
            "response": response
        }

    async def _extract_search_parameters(self, query: str) -> Dict:
        """
        Extract search parameters from a natural language query.
        Uses OpenAI if available, otherwise uses simple pattern matching.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary of extracted parameters
        """
        # Use OpenAI if available for more accurate parameter extraction
        if self.openai_client:
            try:
                logger.info("Using OpenAI to extract search parameters")
                
                system_prompt = """
                You are a product search parameter extractor for a shoe store. Extract parameters from customer queries.
                
                Return a valid JSON object with these fields:
                - brand: Exact brand name mentioned (string or null) - e.g., Nike, Adidas, Puma, New Balance, Reebok
                - category: Product category mentioned (string or null) - e.g., Running, Basketball, Casual, Athletic
                - color: Specific color mentioned (string or null) - be exact with color names
                - size: Exact size mentioned (string or null) - extract both numeric (e.g., "8") and text sizes (e.g., "medium")
                - price_min: Minimum price mentioned (number or null)
                - price_max: Maximum price mentioned (number or null)
                - product_id: Specific product name if mentioned (string or null) - e.g., "Air Max 270", "UltraBoost"
                - search_type: What type of search is this - (options: "specific_product", "browse_category", "filter_search")
                - sort_by: Sort preference if mentioned - (options: "price-asc", "price-desc", null)
                - limit: Number of results to return (number or null) - set to 1 for superlative searches like "most expensive"
                
                For questions about most expensive/highest priced/costliest items, set sort_by to "price-desc" and limit to 1.
                For questions about least expensive/cheapest/lowest priced items, set sort_by to "price-asc" and limit to 1.
                
                Examples:
                "Show me Nike shoes" → {"brand": "Nike", "category": null, "color": null, "size": null, "price_min": null, "price_max": null, "product_id": null, "search_type": "filter_search", "sort_by": null, "limit": null}
                "Do you have Air Max 270 in size 8 and white color" → {"brand": "Nike", "category": null, "color": "white", "size": "8", "price_min": null, "price_max": null, "product_id": "Air Max 270", "search_type": "specific_product", "sort_by": null, "limit": null}
                "What is the most expensive Nike Running shoe" → {"brand": "Nike", "category": "Running", "color": null, "size": null, "price_min": null, "price_max": null, "product_id": null, "search_type": "filter_search", "sort_by": "price-desc", "limit": 1}
                """
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                # Extract parameters from OpenAI response
                content = response.choices[0].message.content
                params = json.loads(content)
                
                # Convert to standard format
                filters = {}
                if params.get("brand"):
                    filters["brand"] = params["brand"]
                if params.get("category"):
                    filters["category"] = params["category"]
                
                # Handle sorting and limiting from OpenAI response
                sort_by = params.get("sort_by")
                limit = params.get("limit")
                
                return {
                    "filters": filters,
                    "sort": sort_by,
                    "limit": limit,
                    **params
                }
            
            except Exception as e:
                logger.error(f"Error extracting parameters with OpenAI: {str(e)}")
                # Fall back to simple pattern matching
        
        # Simple pattern matching for parameter extraction
        logger.info("Using pattern matching to extract search parameters")
        params = {
            "filters": {}
        }
        
        # Extract brand names (basic pattern)
        brand_pattern = r'(?:from|by)\s+(\w+)'
        brand_match = re.search(brand_pattern, query, re.IGNORECASE)
        if brand_match and brand_match.group(1):
            params["brand"] = brand_match.group(1)
            params["filters"]["brand"] = brand_match.group(1)
        
        # Extract categories (basic pattern)
        category_pattern = r'(?:in|for)\s+(\w+)'
        category_match = re.search(category_pattern, query, re.IGNORECASE)
        if category_match and category_match.group(1):
            params["category"] = category_match.group(1)
            params["filters"]["category"] = category_match.group(1)
        
        # Extract colors (basic pattern)
        color_pattern = r'(?:in|color)\s+(\w+)'
        color_match = re.search(color_pattern, query, re.IGNORECASE)
        if color_match and color_match.group(1):
            params["color"] = color_match.group(1)
        
        # Extract sizes (basic pattern)
        size_pattern = r'(?:size)\s+(\w+)'
        size_match = re.search(size_pattern, query, re.IGNORECASE)
        if size_match and size_match.group(1):
            params["size"] = size_match.group(1)
        
        # Extract price range (basic pattern)
        price_min_pattern = r'(?:over|above|min)\s+\$?(\d+)'
        price_min_match = re.search(price_min_pattern, query, re.IGNORECASE)
        if price_min_match and price_min_match.group(1):
            params["price_min"] = float(price_min_match.group(1))
        
        price_max_pattern = r'(?:under|below|max)\s+\$?(\d+)'
        price_max_match = re.search(price_max_pattern, query, re.IGNORECASE)
        if price_max_match and price_max_match.group(1):
            params["price_max"] = float(price_max_match.group(1))
        
        # Handle superlative queries like "highest priced" or "most expensive"
        superlative_pattern = r'(?:highest|most\s+expensive|priciest|costliest)'
        superlative_match = re.search(superlative_pattern, query, re.IGNORECASE)
        if superlative_match:
            params["sort"] = "price-desc"
            params["limit"] = 1
        
        # Handle lowest price queries
        lowest_pattern = r'(?:lowest|least\s+expensive|cheapest)'
        lowest_match = re.search(lowest_pattern, query, re.IGNORECASE)
        if lowest_match:
            params["sort"] = "price-asc"
            params["limit"] = 1
        
        return params
    
    async def get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed information about a product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Dictionary with product details and formatted response
        """
        # Get product details
        product = await self.repository.get_product_by_id(product_id)
        if not product:
            return {
                "error": "Product not found",
                "response": "I'm sorry, I couldn't find that product in our database."
            }
        
        # Format the response
        response = self._format_product_details_response(product)
        
        return {
            "details": product,
            "response": response
        }
    
    async def get_popular_products(self) -> Dict:
        """
        Get a list of popular products.
        
        Returns:
            Dictionary with popular products and formatted response
        """
        # Get featured or popular products (for now, just search without query)
        products = await self.repository.search_products(
            query=None,
            limit=5,
            offset=0
        )
        
        # Format the response
        response = self._format_search_results(products, "popular products")
        
        return {
            "results": products,
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
        logger.info(f"Searching for products in category: {category_name}")
        
        # Normalize the category name for better matching
        normalized_category = category_name.lower().strip()
        
        # First, try to find the exact category in the database
        category_id = None
        category_exact_match = False
        
        # Check for exact or partial matches in category names
        for category in IN_MEMORY_DB["categories"]:
            if category["name"].lower() == normalized_category:
                category_id = category["id"]
                category_exact_match = True
                break
            elif normalized_category in category["name"].lower() or category["name"].lower() in normalized_category:
                category_id = category["id"]
                # Continue looking for exact match
        
        # If we still don't have a category, try to extract category from common terms like "running shoes"
        if not category_id:
            # Check for common category terms in the query
            common_categories = {
                "running": 1,   # Running category ID
                "casual": 2,    # Casual category ID
                "athletic": 3,  # Athletic category ID
                "kids": 4,      # Kids category ID
                "formal": 5     # Formal category ID
            }
            
            for term, id in common_categories.items():
                if term in normalized_category:
                    category_id = id
                    break
        
        # Get products in the category if we found a match
        products = []
        if category_id:
            products = await self.repository.search_products(
                category_id=category_id,
                limit=10,
                offset=0
            )
        
        # If no products found, return all products with a helpful message
        if not products:
            products = await self.repository.search_products(
                limit=5,
                offset=0
            )
            
            # Get all available categories for suggestions
            available_categories = [category["name"] for category in IN_MEMORY_DB["categories"]]
            categories_text = ", ".join(available_categories)
            
            return {
                "products": products,
                "response": f"I'm sorry, I couldn't find any products in the '{category_name}' category. We have these categories available: {categories_text}. Or would you like to see our popular products?"
            }
        
        # Format the response
        actual_category_name = "Unknown"
        for category in IN_MEMORY_DB["categories"]:
            if category["id"] == category_id:
                actual_category_name = category["name"]
                break
        
        response = self._format_category_products_response(products, actual_category_name)
        
        return {
            "products": products,
            "response": response
        }
    
    def _format_search_results(self, products: List[Dict], query: str) -> str:
        """
        Format search results into a natural language response with better suggestions.
        
        Args:
            products: List of product dictionaries
            query: The original search query
            
        Returns:
            Formatted response string
        """
        if not products:
            return f"I'm sorry, I couldn't find any products matching '{query}'. Would you like to browse our popular shoes or see what's on sale?"
        
        # Check if this is a superlative query (highest/lowest price)
        is_highest_query = any(term in query.lower() for term in ["highest", "most expensive", "priciest", "costliest"])
        is_lowest_query = any(term in query.lower() for term in ["lowest", "least expensive", "cheapest"])
        
        # Start with an appropriate introduction
        if is_highest_query:
            if len(products) == 1:
                response_parts = [f"The highest priced product matching '{query.replace('highest', '').replace('most expensive', '').strip()}' is:"]
            else:
                response_parts = [f"Here are the highest priced products matching '{query.replace('highest', '').replace('most expensive', '').strip()}':"]
        elif is_lowest_query:
            if len(products) == 1:
                response_parts = [f"The lowest priced product matching '{query.replace('lowest', '').replace('least expensive', '').replace('cheapest', '').strip()}' is:"]
            else:
                response_parts = [f"Here are the lowest priced products matching '{query.replace('lowest', '').replace('least expensive', '').replace('cheapest', '').strip()}':"]
        elif "popular" in query.lower():
            response_parts = ["Here are some of our popular shoe models:"]
        else:
            response_parts = [f"Here are some products that match your search for '{query}':"]
        
        # Add results
        for i, product in enumerate(products[:5], 1):
            brand = product.get("brand_name", "")
            price_display = f"${product.get('sale_price', 0)}" if product.get("is_on_sale") else f"${product.get('price', 0)}"
            
            # Include relevance score if available
            relevance_info = ""
            if "relevance_score" in product:
                # Only include if it's a high match
                if product["relevance_score"] > 0.7:
                    relevance_info = f" (Strong match: {int(product['relevance_score']*100)}%)"
            
            product_info = f"{i}. **{product.get('name')}** ({brand}) - {price_display}{relevance_info}"
            
            # Add a brief description
            if product.get("description"):
                description = product.get("description")
                # Truncate if too long
                if len(description) > 100:
                    description = description[:97] + "..."
                product_info += f"\n   {description}"
            
            response_parts.append(product_info)
        
        # Add discount information for items on sale
        on_sale_items = [p for p in products[:5] if p.get("is_on_sale")]
        if on_sale_items:
            response_parts.append("\nWe also have these great deals currently on sale:")
            
            for i, product in enumerate(on_sale_items, 1):
                original_price = product.get("price", 0)
                sale_price = product.get("sale_price", 0)
                if original_price and sale_price:
                    discount = ((original_price - sale_price) / original_price) * 100
                    sale_info = f"{i}. **{product.get('name')}** - Was ${original_price}, now ${sale_price} (Save ${original_price - sale_price:.2f}, {discount:.0f}% off)"
                    response_parts.append(sale_info)
        
        # Add a prompt for more details with specific suggestions based on the results
        response_parts.append("\nWould you like more information about any of these shoes? Or are you looking for something specific?")
        
        # Generate specific suggestions based on the results
        suggestions = []
        
        # Add product-specific suggestions
        if products:
            first_product = products[0]
            suggestions.append(f"Tell me more about the {first_product.get('name')}")
        
        # Add category-based suggestions if available
        categories = set(p.get("category_name") for p in products if p.get("category_name"))
        if "Running" in categories:
            suggestions.append("Show me more running shoes")
        elif categories:
            first_category = next(iter(categories))
            suggestions.append(f"Show me more {first_category.lower()} shoes")
        
        # Add brand-based suggestions
        brands = set(p.get("brand_name") for p in products if p.get("brand_name"))
        if brands:
            first_brand = next(iter(brands))
            suggestions.append(f"Do you have other {first_brand} shoes?")
        
        # Add general suggestions
        if "sale" not in query.lower() and on_sale_items:
            suggestions.append("What's on sale?")
        
        # Format and return the full response
        return "\n\n".join(response_parts)
    
    def _format_product_details_response(self, product_details: Dict) -> str:
        """
        Format product details into a natural language response with better suggestions.
        
        Args:
            product_details: Dictionary with product details
            
        Returns:
            Formatted response string
        """
        if not product_details or "error" in product_details:
            return f"I'm sorry, I couldn't find that product. {product_details.get('error', '')} Would you like to see our popular products instead?"
        
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
        
        # Get attributes
        attributes = product_details.get("attributes", {})
        sizes = attributes.get("sizes", [])
        colors = attributes.get("color", [])
        
        # Combine all parts
        response_parts = [
            f"# {name}",
            f"**Brand**: {brand} | **Category**: {category}",
            f"**Price**: {price_text}",
            f"\n{description}\n"
        ]
        
        # Add available sizes and colors if present
        if sizes:
            response_parts.append(f"**Available Sizes**: {', '.join(sizes)}")
        
        if colors:
            response_parts.append(f"**Available Colors**: {', '.join(colors)}")
        
        # Add review information if available
        if review_count > 0:
            stars = "★" * int(avg_rating) + "☆" * (5 - int(avg_rating))
            response_parts.append(f"**Customer Reviews**: {stars} ({avg_rating}/5 based on {review_count} reviews)")
        
        # Add specific suggestions based on the product
        size_suggestion = ""
        color_suggestion = ""
        
        if sizes:
            middle_size = sizes[len(sizes)//2]
            size_suggestion = f"Do you have this in size {middle_size}?"
        
        if colors:
            first_color = colors[0]
            color_suggestion = f"Is this available in {first_color}?"
        
        # Add a prompt for more information with specific suggestions
        suggestions = []
        if sizes and colors:
            suggestions.append(f"Is this available in size {middle_size} and {first_color} color?")
        elif size_suggestion:
            suggestions.append(size_suggestion)
        elif color_suggestion:
            suggestions.append(color_suggestion)
        
        # Add more general questions
        suggestions.append(f"Do you have similar shoes to the {name}?")
        suggestions.append(f"What other {brand} shoes do you have?")
        
        response_parts.append("\nWould you like to check availability of a specific size and color? Or would you like to see similar shoes?")
        
        return "\n".join(response_parts)
    
    def _format_availability_response(self, product: Dict, inventory: Optional[Dict], size: str, color: str) -> str:
        """
        Format availability information into a natural language response with better suggestions.
        
        Args:
            product: Product dictionary
            inventory: Inventory information
            size: Size requested
            color: Color requested
            
        Returns:
            Formatted response string
        """
        name = product.get("name", "Unknown Product")
        brand = product.get("brand_name", "")
        
        if not inventory:
            # Try to suggest alternative sizes or colors
            attributes = product.get("attributes", {})
            available_sizes = attributes.get("sizes", [])
            available_colors = attributes.get("color", [])
            
            # Prepare suggestion text
            suggestions = []
            
            # Find closest alternatives
            available_colors_text = f"We have these colors: {', '.join(available_colors)}." if available_colors else ""
            available_sizes_text = f"We have these sizes: {', '.join(available_sizes)}." if available_sizes else ""
            
            if available_colors and color:
                suggestions.append(f"Show me other colors for {name}")
            
            if available_sizes and size:
                suggestions.append(f"Show me other sizes for {name}")
            
            # Add alternative product suggestions
            suggestions.append(f"Show me similar shoes to {name}")
            suggestions.append(f"What other {brand} shoes do you have?")
            
            return f"I'm sorry, the {name} is not available in size {size} and color {color}. {available_colors_text} {available_sizes_text} Would you like to check a different size or color?"
        
        quantity = inventory.get("quantity", 0)
        
        if quantity <= 0:
            return f"I'm sorry, the {name} is currently out of stock in size {size} and color {color}. Would you like to check a different size or color?"
        elif quantity < 5:
            return f"Good news! The {name} is available in size {size} and color {color}, but we only have {quantity} left in stock. Would you like to add it to your cart?"
        else:
            return f"Great news! The {name} is available in size {size} and color {color}. Would you like to add it to your cart?"
    
    def _format_category_products_response(self, products: List[Dict], category_name: str) -> str:
        """
        Format category products into a natural language response with better category-specific suggestions.
        
        Args:
            products: List of product dictionaries
            category_name: Name of the category
            
        Returns:
            Formatted response string
        """
        if not products:
            # Get available categories for suggestions
            available_categories = [category["name"] for category in IN_MEMORY_DB["categories"]]
            categories_text = ", ".join(available_categories)
            
            return f"I'm sorry, I couldn't find any products in the '{category_name}' category. We have these categories: {categories_text}. Would you like to browse a different category?"
        
        # Start with an introduction
        response_parts = [f"Here are some popular products in the '{category_name}' category:"]
        
        # Add results
        for i, product in enumerate(products[:5], 1):
            brand = product.get("brand_name", "Unknown")
            price_display = f"${product.get('sale_price', 0)}" if product.get("is_on_sale") else f"${product.get('price', 0)}"
            
            product_info = f"{i}. **{product.get('name')}** by {brand} - {price_display}"
            
            # Add a brief description if available
            if product.get("description"):
                description = product.get("description")
                # Truncate if too long
                if len(description) > 100:
                    description = description[:97] + "..."
                product_info += f"\n   {description}"
            
            response_parts.append(product_info)
        
        # Add a prompt for more details with specific category-related suggestions
        response_parts.append("\nWould you like more details about any of these products? Or would you like to see more shoes in this category?")
        
        # Get alternative categories to suggest
        other_categories = []
        for category in IN_MEMORY_DB["categories"]:
            if category["name"] != category_name:
                other_categories.append(category["name"])
        
        # Generate suggestions based on the category
        suggestions = []
        
        # Include specific product suggestions
        if products:
            first_product = products[0]
            suggestions.append(f"Tell me more about the {first_product.get('name')}")
        
        # Add category-specific suggestions
        if category_name.lower() == "running":
            suggestions.append("What running shoes are good for beginners?")
        elif category_name.lower() == "casual":
            suggestions.append("Do you have casual shoes for everyday wear?")
        elif category_name.lower() == "athletic":
            suggestions.append("What are your most popular athletic shoes?")
        
        # Add other category navigation suggestions
        if other_categories:
            suggestions.append(f"Show me {other_categories[0]} shoes instead")
        
        # Add brand-specific suggestions from this category
        brands = set(p.get("brand_name") for p in products if p.get("brand_name"))
        if brands:
            first_brand = next(iter(brands))
            suggestions.append(f"What {first_brand} {category_name.lower()} shoes do you have?")
        
        return "\n".join(response_parts)
    
    async def _is_vector_search_available(self) -> bool:
        """
        Check if vector search is available by trying to initialize vector db
        
        Returns:
            Boolean indicating whether vector search is available
        """
        try:
            vector_db = get_vector_db()
            if vector_db:
                # Try a simple operation to see if it works
                await vector_db.semantic_search("test query", limit=1)
                return True
            return False
        except Exception as e:
            logger.warning(f"Vector search not available: {str(e)}")
            return False 