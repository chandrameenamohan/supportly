#!/usr/bin/env python
"""
Vector Database module for Supportly product search.
This module enables semantic search functionality for product queries.
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
import numpy as np

# Import only IN_MEMORY_DB to avoid circular imports
from .db_connection import IN_MEMORY_DB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path for persistent vector db
VECTOR_DB_PATH = os.environ.get("VECTOR_DB_PATH", "./vector_db")

class VectorDatabase:
    """
    Vector database for semantic product search using Chroma.
    Provides functionality to convert product data to embeddings and perform semantic search.
    """
    
    def __init__(self, persist_directory: Optional[str] = VECTOR_DB_PATH):
        """
        Initialize the vector database.
        
        Args:
            persist_directory: Directory to persist the vector database
        """
        self.persist_directory = persist_directory
        
        # Create embedding function (OpenAI by default)
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        # Initialize Chroma client - Updated to use new client format
        if persist_directory:
            # Create the directory if it doesn't exist
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()
        
        # Create or get collection for products
        self.collection = self.client.get_or_create_collection(
            name="products",
            embedding_function=self.embedding_function,
            metadata={"description": "Supportly product database"}
        )
        
        logger.info("Vector database initialized")
    
    async def index_products(self):
        """
        Index all products in the database to the vector store.
        Creates embeddings for product data for semantic search.
        """
        logger.info("Indexing products to vector database")
        
        # Get all products from in-memory database
        products = IN_MEMORY_DB["products"]
        
        if not products:
            logger.warning("No products found to index")
            return
        
        # Prepare data for batch insertion
        ids = []
        documents = []
        metadatas = []
        
        for product in products:
            # Create document from product data (combine name and description for better results)
            document = f"{product['name']} - {product['description']}"
            
            # Get brand and category names
            brand_name = "Unknown Brand"
            for brand in IN_MEMORY_DB["brands"]:
                if brand["id"] == product["brand_id"]:
                    brand_name = brand["name"]
                    break
            
            category_name = "Unknown Category"
            for category in IN_MEMORY_DB["categories"]:
                if category["id"] == product["category_id"]:
                    category_name = category["name"]
                    break
            
            # Create searchable metadata
            metadata = {
                "id": product["id"],
                "name": product["name"],
                "brand": brand_name,
                "category": category_name,
                "price": str(product["price"]),
                "is_on_sale": str(product["is_on_sale"]),
                "sale_price": str(product["sale_price"]) if product["sale_price"] else "",
            }
            
            # Add sizes and colors from attributes if they exist
            if "attributes" in product:
                if "sizes" in product["attributes"]:
                    metadata["sizes"] = ", ".join(product["attributes"]["sizes"])
                if "color" in product["attributes"]:
                    metadata["colors"] = ", ".join(product["attributes"]["color"])
            
            # Ensure no None values in metadata (ChromaDB requirement)
            for key in metadata:
                if metadata[key] is None:
                    metadata[key] = ""
            
            ids.append(product["id"])
            documents.append(document)
            metadatas.append(metadata)
        
        # Clear existing collection (for re-indexing)
        try:
            # Delete all documents using a valid where filter
            self.collection.delete(where={"id": {"$ne": "non_existent_id"}})
        except Exception as e:
            logger.warning(f"Error clearing collection: {str(e)}. Proceeding with adding documents.")
        
        # Batch add to collection
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Indexed {len(products)} products to vector database")
    
    async def semantic_search(
        self, 
        query: str, 
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform semantic search for products based on natural language query.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            filters: Dictionary of filters to apply to the search
            
        Returns:
            List of product dictionaries matching the query
        """
        logger.info(f"Performing semantic search for: '{query}'")
        
        # Prepare filter if specified
        where_clause = None
        if filters:
            # Build a more comprehensive where clause
            filter_conditions = {}
            
            if filters.get("brand"):
                filter_conditions["brand"] = {"$eq": filters["brand"]}
            
            if filters.get("category"):
                filter_conditions["category"] = {"$eq": filters["category"]}
            
            # Only use the first filter condition to avoid ChromaDB complexity limitations
            if filter_conditions:
                # Use the first filter only (ChromaDB has limitations with complex filters)
                key, value = next(iter(filter_conditions.items()))
                where_clause = {key: value}
        
        try:
            # Adjust query if needed for better search results
            search_query = query
            
            # If query is too short or generic, enhance it
            if len(query.split()) <= 2 and "shoes" not in query.lower():
                search_query = f"{query} shoes"
            
            # Execute search
            results = self.collection.query(
                query_texts=[search_query],
                n_results=min(limit, 20),  # Limit to 20 max for efficiency but allow smaller values
                where=where_clause
            )
            
            # No results found
            if not results or not results["metadatas"] or not results["metadatas"][0]:
                logger.info(f"No results found for query: '{search_query}'")
                return []
            
            # Process results
            product_ids = [metadata["id"] for metadata in results["metadatas"][0]]
            distances = results.get("distances", [[]])[0]
            documents = results.get("documents", [[]])
            
            # Get full product details for each result
            products = []
            for i, product_id in enumerate(product_ids):
                # Find product with matching ID
                for product in IN_MEMORY_DB["products"]:
                    if product["id"] == product_id:
                        result = product.copy()
                        
                        # Add relevance score
                        if distances and i < len(distances):
                            # Convert distance to similarity score (1 - distance) and round to 2 decimals
                            result["relevance_score"] = round(1 - distances[i], 2)
                        
                        # Add brand and category names
                        for brand in IN_MEMORY_DB["brands"]:
                            if brand["id"] == product["brand_id"]:
                                result["brand_name"] = brand["name"]
                                break
                        
                        for category in IN_MEMORY_DB["categories"]:
                            if category["id"] == product["category_id"]:
                                result["category_name"] = category["name"]
                                break
                        
                        products.append(result)
                        break
            
            # Post-process results to apply additional filters
            if filters:
                # Apply additional filters that ChromaDB might not handle well
                filtered_products = products.copy()
                
                # Filter by price range if provided
                if filters.get("price_min") is not None:
                    price_min = float(filters["price_min"])
                    filtered_products = [p for p in filtered_products if 
                                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) >= price_min]
                
                if filters.get("price_max") is not None:
                    price_max = float(filters["price_max"])
                    filtered_products = [p for p in filtered_products if 
                                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) <= price_max]
                
                # Only update products if we have results after filtering
                if filtered_products:
                    products = filtered_products
            
            logger.info(f"Found {len(products)} products for query: '{search_query}'")
            return products
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            # Try a basic search if semantic search fails
            try:
                # Fall back to a very simple search for products matching name
                query_terms = query.lower().split()
                basic_results = []
                
                for product in IN_MEMORY_DB["products"]:
                    name_lower = product["name"].lower()
                    # Check if any query term is in the product name
                    if any(term in name_lower for term in query_terms):
                        product_copy = product.copy()
                        
                        # Add brand and category names
                        for brand in IN_MEMORY_DB["brands"]:
                            if brand["id"] == product["brand_id"]:
                                product_copy["brand_name"] = brand["name"]
                                break
                        
                        for category in IN_MEMORY_DB["categories"]:
                            if category["id"] == product["category_id"]:
                                product_copy["category_name"] = category["name"]
                                break
                        
                        basic_results.append(product_copy)
                
                logger.info(f"Fallback search found {len(basic_results)} products")
                return basic_results[:limit]
            except Exception as inner_e:
                logger.error(f"Error in fallback search: {str(inner_e)}")
                return []
    
    def extract_search_filters(self, query: str) -> Dict:
        """
        Extract search filters from a natural language query using an LLM.
        This is a placeholder for future LLM-based filter extraction.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary of extracted filters
        """
        # This method could be expanded to use an LLM to extract filters
        # For now, return an empty dictionary
        return {} 