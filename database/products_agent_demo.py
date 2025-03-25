#!/usr/bin/env python
"""
Demo showing how the products agent would use the shoe product database.
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Union
import asyncio
import datetime

# PostgreSQL specific imports
# In a real implementation, these would be properly set up
# For this demo, we'll simulate the database with JSON files
# import asyncpg
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import sessionmaker

class ProductsAgent:
    """
    Simulated agent that queries the product database to answer customer questions.
    
    In a real implementation, this would connect to PostgreSQL.
    For this demo, we'll load the JSON data files.
    """
    
    def __init__(self, data_dir: str = "database/data"):
        """Initialize the agent with path to data files."""
        self.data_dir = data_dir
        self.data = {}
        self.load_data()
    
    def load_data(self):
        """Load all JSON data files."""
        data_files = ["brands", "categories", "products", "inventory", "reviews", "product_relations"]
        
        for file_name in data_files:
            file_path = os.path.join(self.data_dir, f"{file_name}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.data[file_name] = json.load(f)
            else:
                print(f"Warning: {file_path} not found.")
                self.data[file_name] = []
        
        print(f"Loaded data: {len(self.data.get('products', []))} products, {len(self.data.get('inventory', []))} inventory items")
    
    def search_products(self, 
                        query: str, 
                        category_id: Optional[int] = None,
                        brand_id: Optional[int] = None,
                        price_range: Optional[tuple] = None,
                        size: Optional[str] = None,
                        color: Optional[str] = None,
                        limit: int = 5) -> List[Dict]:
        """
        Search for products matching criteria.
        
        Args:
            query: Search terms
            category_id: Filter by category ID
            brand_id: Filter by brand ID
            price_range: Tuple of (min_price, max_price)
            size: Filter by shoe size
            color: Filter by color
            limit: Maximum number of results
        
        Returns:
            List of matching products
        """
        # Convert query to lowercase for case-insensitive matching
        query = query.lower()
        
        # Filter products based on search criteria
        results = []
        for product in self.data.get("products", []):
            # Skip non-active products
            if not product.get("is_active", True):
                continue
            
            # Check if query matches name or description
            matches_query = query in product.get("name", "").lower() or query in product.get("description", "").lower()
            
            # Check if query matches any metadata keywords
            metadata = product.get("metadata", {})
            keywords = metadata.get("search_keywords", [])
            for keyword in keywords:
                if query in str(keyword).lower():
                    matches_query = True
                    break
            
            # Skip if query doesn't match
            if not matches_query and query != "":
                continue
            
            # Filter by category
            if category_id is not None and product.get("category_id") != category_id:
                continue
            
            # Filter by brand
            if brand_id is not None and product.get("brand_id") != brand_id:
                continue
            
            # Filter by price range
            if price_range is not None:
                min_price, max_price = price_range
                product_price = product.get("sale_price") if product.get("is_on_sale") else product.get("price")
                if product_price < min_price or product_price > max_price:
                    continue
            
            # Add product to results
            results.append(product)
        
        # Filter by size and color using inventory
        if size is not None or color is not None:
            filtered_results = []
            for product in results:
                product_id = product.get("id")
                
                # Find inventory items for this product
                inventory_items = [
                    item for item in self.data.get("inventory", [])
                    if item.get("product_id") == product_id
                ]
                
                # Check if product has inventory matching size and color
                has_match = False
                for item in inventory_items:
                    size_match = size is None or item.get("size") == size
                    color_match = color is None or item.get("color").lower() == color.lower()
                    quantity = item.get("quantity", 0)
                    
                    if size_match and color_match and quantity > 0:
                        has_match = True
                        break
                
                if has_match:
                    filtered_results.append(product)
            
            results = filtered_results
        
        # Sort results by relevance (for now, featured items first)
        results = sorted(results, key=lambda p: (0 if p.get("is_featured") else 1))
        
        # Limit results
        return results[:limit]
    
    def get_product_details(self, product_id: str) -> Dict:
        """
        Get detailed information about a specific product.
        
        Args:
            product_id: The UUID of the product
            
        Returns:
            Product details with inventory, reviews, and related products
        """
        # Find the product
        product = None
        for p in self.data.get("products", []):
            if p.get("id") == product_id:
                product = p
                break
        
        if product is None:
            return {"error": "Product not found"}
        
        # Get brand info
        brand = None
        for b in self.data.get("brands", []):
            if b.get("id") == product.get("brand_id"):
                brand = b
                break
        
        # Get category info
        category = None
        for c in self.data.get("categories", []):
            if c.get("id") == product.get("category_id"):
                category = c
                break
        
        # Get inventory info
        inventory = [
            item for item in self.data.get("inventory", [])
            if item.get("product_id") == product_id
        ]
        
        # Get reviews
        reviews = [
            review for review in self.data.get("reviews", [])
            if review.get("product_id") == product_id
        ]
        
        # Calculate average rating
        avg_rating = 0
        if reviews:
            avg_rating = sum(review.get("rating", 0) for review in reviews) / len(reviews)
        
        # Get related products
        related_product_ids = [
            relation.get("related_product_id")
            for relation in self.data.get("product_relations", [])
            if relation.get("product_id") == product_id
        ]
        
        related_products = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "price": p.get("price")
            }
            for p in self.data.get("products", [])
            if p.get("id") in related_product_ids
        ]
        
        # Construct detailed product info
        product_details = {
            "id": product_id,
            "name": product.get("name"),
            "description": product.get("description"),
            "sku": product.get("sku"),
            "brand": brand.get("name") if brand else None,
            "category": category.get("name") if category else None,
            "price": product.get("price"),
            "sale_price": product.get("sale_price"),
            "is_on_sale": product.get("is_on_sale"),
            "attributes": product.get("attributes"),
            "images": product.get("images"),
            "inventory": inventory,
            "reviews": {
                "count": len(reviews),
                "average_rating": round(avg_rating, 1),
                "latest": reviews[:3] if reviews else []
            },
            "related_products": related_products
        }
        
        return product_details
    
    def check_inventory(self, product_id: str, size: str, color: str) -> Dict:
        """
        Check if a specific product variant is in stock.
        
        Args:
            product_id: The UUID of the product
            size: The requested size
            color: The requested color
            
        Returns:
            Inventory information
        """
        # Find matching inventory item
        for item in self.data.get("inventory", []):
            if (item.get("product_id") == product_id and
                    item.get("size") == size and
                    item.get("color").lower() == color.lower()):
                
                quantity = item.get("quantity", 0)
                return {
                    "in_stock": quantity > 0,
                    "quantity": quantity,
                    "size": size,
                    "color": color,
                    "location": item.get("location_data", {}).get("warehouse")
                }
        
        return {
            "in_stock": False,
            "error": "Product variant not found"
        }
    
    def get_category_products(self, category_name: str, limit: int = 10) -> List[Dict]:
        """
        Get products in a specific category.
        
        Args:
            category_name: The name of the category
            limit: Maximum number of results
            
        Returns:
            List of products in the category
        """
        # Find category ID
        category_id = None
        for category in self.data.get("categories", []):
            if category.get("name").lower() == category_name.lower():
                category_id = category.get("id")
                break
        
        if category_id is None:
            return []
        
        # Find products in this category
        products = [
            product for product in self.data.get("products", [])
            if product.get("category_id") == category_id and product.get("is_active", True)
        ]
        
        # Sort by featured and price
        products = sorted(products, key=lambda p: (0 if p.get("is_featured") else 1, p.get("price", 0)))
        
        # Return simplified product data
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "brand_id": p.get("brand_id"),
                "price": p.get("price"),
                "sale_price": p.get("sale_price"),
                "is_on_sale": p.get("is_on_sale")
            }
            for p in products[:limit]
        ]
    
    def answer_product_question(self, question: str) -> str:
        """
        Simulates how the agent would answer a product-related question.
        
        Args:
            question: The customer's question
            
        Returns:
            Agent's response
        """
        question = question.lower()
        
        # Check if question is about available products
        if "running shoes" in question:
            products = self.search_products("running", category_id=6, limit=3)
            if products:
                response = "We have several running shoes available. Here are some options:\n\n"
                for product in products:
                    price = product.get("sale_price") if product.get("is_on_sale") else product.get("price")
                    response += f"- {product.get('name')}: ${price}\n"
                response += "\nWould you like more details about any of these?"
                return response
            else:
                return "I'm sorry, we don't have any running shoes in stock at the moment."
        
        # Check if question is about a specific product
        if "air force 1" in question:
            products = self.search_products("Air Force 1")
            if products:
                product = products[0]
                details = self.get_product_details(product.get("id"))
                
                response = f"The {details.get('name')} is a {details.get('attributes', {}).get('gender')} shoe "
                response += f"priced at ${details.get('price')}. "
                
                # Add information about colors and sizes
                colors = set(item.get("color") for item in details.get("inventory", []) if item.get("quantity", 0) > 0)
                sizes = set(item.get("size") for item in details.get("inventory", []) if item.get("quantity", 0) > 0)
                
                if colors:
                    response += f"It's available in {', '.join(colors)}. "
                
                if sizes:
                    response += f"Available sizes include {', '.join(sorted(sizes))}. "
                
                response += f"\n\nKey features include:\n"
                for feature in details.get("attributes", {}).get("features", [])[:3]:
                    response += f"- {feature}\n"
                
                response += f"\nThe average rating is {details.get('reviews', {}).get('average_rating')} stars based on "
                response += f"{details.get('reviews', {}).get('count')} reviews."
                
                return response
            else:
                return "I'm sorry, I couldn't find information about Nike Air Force 1 shoes."
        
        # Check if question is about inventory
        if "size" in question and "color" in question:
            # Extract size and color (simplified)
            size = None
            for word in question.split():
                if word.replace(".", "").isdigit():
                    size = word
                    break
            
            color = None
            for potential_color in ["black", "white", "red", "blue", "green"]:
                if potential_color in question:
                    color = potential_color
                    break
            
            if size and color:
                # Use the first product from search results for demo
                products = self.search_products("", limit=1)
                if products:
                    product_id = products[0].get("id")
                    inventory = self.check_inventory(product_id, size, color)
                    
                    if inventory.get("in_stock"):
                        return f"Yes, we have size {size} in {color} available. There are {inventory.get('quantity')} pairs in stock."
                    else:
                        return f"I'm sorry, we don't currently have size {size} in {color} in stock."
            
            return "I need both a size and color to check inventory. Could you specify which size and color you're looking for?"
        
        # Default response
        return "I can help you find shoes from our catalog. Could you tell me what type of shoes you're looking for?"


# Demo function to simulate customer interactions
def demo():
    """Run a demo of the products agent."""
    print("--- Supportly Shoe Store Products Agent Demo ---\n")
    
    # Initialize the agent
    agent = ProductsAgent()
    print("\n")
    
    # Demo questions
    questions = [
        "Do you have any running shoes?",
        "Tell me about Nike Air Force 1.",
        "Do you have size 10 in black?",
        "What basketball shoes do you recommend?"
    ]
    
    for question in questions:
        print(f"Customer: {question}\n")
        response = agent.answer_product_question(question)
        print(f"Agent: {response}\n")
        print("-" * 70)
        print()


if __name__ == "__main__":
    # Check if data files exist
    if not os.path.exists("database/data/products.json"):
        print("Data files not found. Please run seed_data.py first.")
        sys.exit(1)
    
    demo() 