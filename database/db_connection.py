#!/usr/bin/env python
"""
Database connection module for the Supportly product database.
This module handles an in-memory database for products.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Union
import uuid
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# In-memory database storage - initialized with sample data
IN_MEMORY_DB = {
    "brands": [
        {"id": 1, "name": "Nike", "description": "Athletic footwear and apparel"},
        {"id": 2, "name": "Adidas", "description": "Sports shoes and clothing"},
        {"id": 3, "name": "New Balance", "description": "Performance athletic shoes"},
        {"id": 4, "name": "Puma", "description": "Sports and casual footwear"},
        {"id": 5, "name": "Reebok", "description": "Athletic footwear brand"}
    ],
    "categories": [
        {"id": 1, "name": "Running", "description": "Shoes designed for running and jogging"},
        {"id": 2, "name": "Casual", "description": "Everyday comfortable shoes"},
        {"id": 3, "name": "Athletic", "description": "General sports shoes"},
        {"id": 4, "name": "Kids", "description": "Shoes for children"},
        {"id": 5, "name": "Formal", "description": "Dress shoes for formal occasions"}
    ],
    "products": [
        {
            "id": str(uuid.uuid4()),
            "sku": "NIKE-AIR-001",
            "name": "Nike Air Max 270",
            "description": "The Nike Air Max 270 delivers visible cushioning under every step with a large window and 270 degrees of Air.",
            "brand_id": 1,
            "category_id": 1,
            "price": 150.00,
            "sale_price": 129.99,
            "is_on_sale": True,
            "attributes": {"color": ["black", "white", "red"], "sizes": ["7", "8", "9", "10", "11"]}
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "ADIDAS-ULTRA-001",
            "name": "Adidas UltraBoost",
            "description": "Ultraboost shoes with responsive cushioning and a sock-like fit.",
            "brand_id": 2,
            "category_id": 1,
            "price": 180.00,
            "sale_price": None,
            "is_on_sale": False,
            "attributes": {"color": ["blue", "grey", "white"], "sizes": ["7", "8", "9", "10", "11", "12"]}
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "NB-990-001",
            "name": "New Balance 990",
            "description": "The 990 is the iconic New Balance style that blends cushioning and stability.",
            "brand_id": 3,
            "category_id": 3,
            "price": 175.00,
            "sale_price": 149.99,
            "is_on_sale": True,
            "attributes": {"color": ["grey", "navy"], "sizes": ["8", "9", "10", "11"]}
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "PUMA-RS-001",
            "name": "Puma RS-X",
            "description": "The Puma RS-X features bold design, vibrant colors and retro appeal.",
            "brand_id": 4,
            "category_id": 2,
            "price": 110.00,
            "sale_price": 89.99,
            "is_on_sale": True,
            "attributes": {"color": ["white", "black", "yellow"], "sizes": ["7", "8", "9", "10", "11"]}
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "REEBOK-CL-001",
            "name": "Reebok Classic Leather",
            "description": "The Reebok Classic Leather features a timeless design and premium materials.",
            "brand_id": 5,
            "category_id": 2,
            "price": 80.00,
            "sale_price": None,
            "is_on_sale": False,
            "attributes": {"color": ["white", "black", "cream"], "sizes": ["6", "7", "8", "9", "10", "11"]}
        }
    ]
}

# Function to load all available data from JSON files
def load_data_from_files():
    """Load data from JSON files in the database/data directory into IN_MEMORY_DB."""
    global IN_MEMORY_DB
    
    data_dir = "database/data"
    data_files = ["brands", "categories", "products", "inventory", "reviews", "product_relations"]
    
    # Check if the data directory exists
    if not os.path.exists(data_dir):
        logger.warning(f"Data directory {data_dir} not found. Using sample data.")
        return
    
    # Load each file
    for file_name in data_files:
        file_path = os.path.join(data_dir, f"{file_name}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    IN_MEMORY_DB[file_name] = data
                    logger.info(f"Loaded {len(data)} records from {file_path}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
        else:
            logger.warning(f"Data file {file_path} not found.")
    
    logger.info(f"Loaded data: {len(IN_MEMORY_DB.get('products', []))} products, {len(IN_MEMORY_DB.get('inventory', []))} inventory items")

# Load data at module initialization time
load_data_from_files()

class DatabaseConnection:
    """
    Manages in-memory database operations for the products database.
    """
    
    @classmethod
    async def get_pool(cls, config: Optional[Dict] = None):
        """
        Simulate getting a connection pool (no-op for in-memory database).
        
        Args:
            config: Optional database configuration override (ignored)
            
        Returns:
            None
        """
        logger.info("Using in-memory database")
        return None
    
    @classmethod
    async def close_pool(cls):
        """Close the connection pool (no-op for in-memory database)."""
        logger.info("In-memory database connection closed")
    
    @classmethod
    async def execute_query(cls, query: str, *args) -> List[Dict]:
        """
        Simulate executing a query against the in-memory database.
        This simplified implementation supports basic query patterns.
        
        Args:
            query: SQL-like query string
            *args: Query parameters
            
        Returns:
            List of dictionaries with query results
        """
        # Parse the query to determine what data to return
        query_lower = query.lower()
        
        try:
            # Handle SELECT queries for products
            if "select" in query_lower and "from products" in query_lower:
                # Basic filtering
                results = IN_MEMORY_DB["products"]
                
                # Apply WHERE clause simulation
                if "where" in query_lower:
                    for arg in args:
                        if isinstance(arg, str) and arg.strip():
                            # Simple string matching for demonstration
                            results = [p for p in results if 
                                      arg.lower() in p["name"].lower() or 
                                      arg.lower() in p["description"].lower()]
                
                return results
                
            # Handle SELECT queries for brands
            elif "select" in query_lower and "from brands" in query_lower:
                return IN_MEMORY_DB["brands"]
                
            # Handle SELECT queries for categories
            elif "select" in query_lower and "from categories" in query_lower:
                return IN_MEMORY_DB["categories"]
                
            # Return empty result for unsupported queries
            else:
                logger.warning(f"Unsupported query pattern: {query}")
                return []
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            return []
    
    @classmethod
    async def execute_transaction(cls, *queries_and_args) -> List[List[Dict]]:
        """
        Simulate executing multiple queries in a transaction.
        
        Args:
            *queries_and_args: Tuples of (query, args)
            
        Returns:
            List of results for each query
        """
        results = []
        for query_and_args in queries_and_args:
            query = query_and_args[0]
            args = query_and_args[1] if len(query_and_args) > 1 else []
            result = await cls.execute_query(query, *args)
            results.append(result)
        return results

# Singleton instance for easy import
db = DatabaseConnection 