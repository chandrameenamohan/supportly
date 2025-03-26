#!/usr/bin/env python
"""
Repository module for product database operations.
This module contains all the database queries for products.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from .db_connection import db, IN_MEMORY_DB
from .vector_db import VectorDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instance of VectorDatabase
_vector_db = None

def get_vector_db():
    """Get or initialize the vector database instance."""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase()
    return _vector_db

class ProductsRepository:
    """
    Repository for product database operations.
    Implements queries for all product-related functionality.
    """

    @staticmethod
    async def search_products(
        query: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        use_semantic_search: bool = True
    ) -> List[Dict]:
        """
        Search for products with filters.
        
        Args:
            query: Text search query
            category_id: Filter by category ID
            brand_id: Filter by brand ID
            price_min: Minimum price
            price_max: Maximum price
            size: Filter by size
            color: Filter by color
            limit: Maximum number of results
            offset: Offset for pagination
            use_semantic_search: Whether to use semantic search (vector DB) or standard search
            
        Returns:
            List of product dictionaries
        """
        try:
            # Use hybrid search approach if query is provided
            if query:
                return await ProductsRepository.hybrid_search(
                    query=query,
                    category_id=category_id,
                    brand_id=brand_id,
                    price_min=price_min,
                    price_max=price_max,
                    size=size,
                    color=color,
                    limit=limit,
                    offset=offset,
                    use_semantic_search=use_semantic_search
                )
            
            # Standard search (no query provided) using SQL-based filtering
            else:
                # SQL query to filter products
                sql = """
                SELECT 
                    p.id, p.sku, p.name, p.description,
                    p.brand_id, b.name as brand_name,
                    p.category_id, c.name as category_name,
                    p.price, p.sale_price, p.is_on_sale,
                    p.is_featured, p.attributes
                FROM 
                    products p
                JOIN 
                    brands b ON p.brand_id = b.id
                JOIN 
                    categories c ON p.category_id = c.id
                WHERE 
                    p.is_active = TRUE
                """
                
                params = []
                param_count = 0
                
                # Add WHERE clauses
                if category_id is not None:
                    param_count += 1
                    sql += f" AND p.category_id = ${param_count}"
                    params.append(category_id)
                
                if brand_id is not None:
                    param_count += 1
                    sql += f" AND p.brand_id = ${param_count}"
                    params.append(brand_id)
                
                if price_min is not None:
                    param_count += 1
                    sql += f" AND (CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END) >= ${param_count}"
                    params.append(price_min)
                
                if price_max is not None:
                    param_count += 1
                    sql += f" AND (CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END) <= ${param_count}"
                    params.append(price_max)
                
                # Add sorting
                sql += """
                ORDER BY 
                    p.is_featured DESC,
                    CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END
                """
                
                # Add limit and offset
                param_count += 1
                sql += f" LIMIT ${param_count}"
                params.append(limit)
                
                param_count += 1
                sql += f" OFFSET ${param_count}"
                params.append(offset)
                
                try:
                    # Execute SQL query
                    results = await db.execute_query(sql, *params)
                    
                    # Post-process results to handle size and color filtering
                    # (since these are in the JSONB attributes field)
                    if size is not None or color is not None:
                        filtered_results = []
                        for product in results:
                            attributes = product.get("attributes", {})
                            if size is not None and "sizes" in attributes:
                                if size not in attributes["sizes"]:
                                    continue
                            if color is not None and "color" in attributes:
                                if color not in attributes["color"]:
                                    continue
                            filtered_results.append(product)
                        
                        results = filtered_results
                    
                    return results
                    
                except Exception as e:
                    logger.error(f"SQL query error: {str(e)}")
                    # Fallback to in-memory filtering
                    return ProductsRepository._fallback_search(
                        category_id=category_id,
                        brand_id=brand_id,
                        price_min=price_min,
                        price_max=price_max,
                        size=size,
                        color=color,
                        limit=limit,
                        offset=offset
                    )
                
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []

    @staticmethod
    async def hybrid_search(
        query: str,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        use_semantic_search: bool = True
    ) -> List[Dict]:
        """
        Hybrid search combining vector database for semantic understanding 
        and SQL for precise filtering.
        
        Args:
            query: Natural language search query
            category_id: Filter by category ID
            brand_id: Filter by brand ID
            price_min: Minimum price
            price_max: Maximum price
            size: Filter by size
            color: Filter by color
            limit: Maximum number of results
            offset: Offset for pagination
            use_semantic_search: Whether to use semantic search
            
        Returns:
            List of product dictionaries
        """
        # Step 1: Use vector search to identify semantically relevant products
        if use_semantic_search:
            logger.info(f"Using semantic search for query: {query}")
            
            # Create filter dict for vector search (fewer filters for broader initial results)
            vector_filters = {}
            
            # Add category and brand filters to vector search if provided
            if category_id is not None:
                for category in IN_MEMORY_DB["categories"]:
                    if category["id"] == category_id:
                        vector_filters["category"] = category["name"]
                        break
            
            if brand_id is not None:
                for brand in IN_MEMORY_DB["brands"]:
                    if brand["id"] == brand_id:
                        vector_filters["brand"] = brand["name"]
                        break
            
            # Perform semantic search with minimal filters
            vector_db = get_vector_db()
            candidates = await vector_db.semantic_search(
                query, 
                limit=min(limit * 3, 50),  # Get more candidates than needed
                filters=vector_filters
            )
            
            if not candidates:
                logger.info("No results from vector search, trying fallback search")
                candidates = []
            else:
                # Get product IDs for SQL filtering
                product_ids = [p["id"] for p in candidates]
                
                # Step 2: Apply precise SQL filtering to the candidates from vector search
                if product_ids and (price_min is not None or price_max is not None or 
                                   size is not None or color is not None):
                    
                    sql = """
                    SELECT 
                        p.id, p.sku, p.name, p.description,
                        p.brand_id, b.name as brand_name,
                        p.category_id, c.name as category_name,
                        p.price, p.sale_price, p.is_on_sale,
                        p.is_featured, p.attributes
                    FROM 
                        products p
                    JOIN 
                        brands b ON p.brand_id = b.id
                    JOIN 
                        categories c ON p.category_id = c.id
                    WHERE 
                        p.is_active = TRUE
                        AND p.id = ANY($1)
                    """
                    
                    params = [product_ids]
                    param_count = 1
                    
                    # Add price filters
                    if price_min is not None:
                        param_count += 1
                        sql += f" AND (CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END) >= ${param_count}"
                        params.append(price_min)
                    
                    if price_max is not None:
                        param_count += 1
                        sql += f" AND (CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END) <= ${param_count}"
                        params.append(price_max)
                    
                    try:
                        # Execute SQL query for additional filtering
                        sql_results = await db.execute_query(sql, *params)
                        
                        # Post-process for size and color
                        if size is not None or color is not None:
                            filtered_results = []
                            for product in sql_results:
                                attributes = product.get("attributes", {})
                                if size is not None and "sizes" in attributes:
                                    if size not in attributes["sizes"]:
                                        continue
                                if color is not None and "color" in attributes:
                                    if color not in attributes["color"]:
                                        continue
                                filtered_results.append(product)
                            
                            sql_results = filtered_results
                        
                        # Reorder SQL results based on vector search relevance
                        ordered_results = []
                        for candidate in candidates:
                            for sql_result in sql_results:
                                if candidate["id"] == sql_result["id"]:
                                    # Combine results, preserving relevance score
                                    combined = sql_result.copy()
                                    if "relevance_score" in candidate:
                                        combined["relevance_score"] = candidate["relevance_score"]
                                    ordered_results.append(combined)
                                    break
                        
                        # Return results with pagination
                        return ordered_results[offset:offset+limit]
                        
                    except Exception as e:
                        logger.error(f"Error in SQL filtering: {str(e)}")
                        # Fallback to in-memory filtering of vector results
                        return ProductsRepository._filter_candidates(
                            candidates, 
                            price_min=price_min,
                            price_max=price_max,
                            size=size,
                            color=color,
                            limit=limit,
                            offset=offset
                        )
                
                # If no additional filtering needed, just return vector results with pagination
                return candidates[offset:offset+limit]
        
        # Fallback to standard search if semantic search is disabled or failed
        logger.info("Falling back to standard search")
        
        return ProductsRepository._fallback_search(
            query=query,
            category_id=category_id,
            brand_id=brand_id,
            price_min=price_min,
            price_max=price_max,
            size=size,
            color=color,
            limit=limit,
            offset=offset
        )

    @staticmethod
    def _filter_candidates(
        candidates: List[Dict],
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        Filter candidate products from vector search using in-memory filtering.
        
        Args:
            candidates: List of candidate products from vector search
            price_min: Minimum price
            price_max: Maximum price
            size: Filter by size
            color: Filter by color
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Filtered list of product dictionaries
        """
        # Apply filters
        results = candidates.copy()
        
        if price_min is not None:
            results = [p for p in results if 
                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) >= price_min]
        
        if price_max is not None:
            results = [p for p in results if 
                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) <= price_max]
        
        if size is not None:
            results = [p for p in results if 
                      "attributes" in p and
                      "sizes" in p["attributes"] and 
                      size in p["attributes"]["sizes"]]
        
        if color is not None:
            results = [p for p in results if 
                      "attributes" in p and
                      "color" in p["attributes"] and 
                      color in p["attributes"]["color"]]
        
        # Apply pagination
        return results[offset:offset+limit]

    @staticmethod
    def _fallback_search(
        query: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fallback search using in-memory filtering when SQL or vector search fails.
        
        Args:
            query: Text search query
            category_id: Filter by category ID
            brand_id: Filter by brand ID
            price_min: Minimum price
            price_max: Maximum price
            size: Filter by size
            color: Filter by color
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of product dictionaries
        """
        # Start with all products
        results = IN_MEMORY_DB["products"].copy()
        
        # Apply text search filter
        if query:
            query_lower = query.lower()
            
            # Extract potential brands and categories from query
            brands = {b["name"].lower(): b["id"] for b in IN_MEMORY_DB["brands"]}
            categories = {c["name"].lower(): c["id"] for c in IN_MEMORY_DB["categories"]}
            
            # Check if query contains any brand names
            brand_matches = []
            for brand_name, brand_id in brands.items():
                if brand_name in query_lower:
                    brand_matches.append(brand_id)
            
            # Check if query contains any category names
            category_matches = []
            for category_name, category_id in categories.items():
                if category_name in query_lower:
                    category_matches.append(category_id)
            
            if brand_matches and "shoes" in query_lower:
                # Handle "Nike shoes" type queries - find all products by that brand
                results = [p for p in results if p["brand_id"] in brand_matches]
            elif category_matches and "shoes" in query_lower:
                # Handle "running shoes" type queries - find all products in that category
                results = [p for p in results if p["category_id"] in category_matches]
            else:
                # Standard text search in name and description
                results = [p for p in results if 
                          query_lower in p["name"].lower() or 
                          query_lower in p["description"].lower()]
        
        # Apply other filters
        if category_id is not None:
            results = [p for p in results if p["category_id"] == category_id]
            
        if brand_id is not None:
            results = [p for p in results if p["brand_id"] == brand_id]
            
        if price_min is not None:
            results = [p for p in results if 
                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) >= price_min]
            
        if price_max is not None:
            results = [p for p in results if 
                      (p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]) <= price_max]
        
        if size is not None:
            results = [p for p in results if 
                      "attributes" in p and
                      "sizes" in p["attributes"] and 
                      size in p["attributes"]["sizes"]]
            
        if color is not None:
            results = [p for p in results if 
                      "attributes" in p and
                      "color" in p["attributes"] and 
                      color in p["attributes"]["color"]]
        
        # Sort by featured status and then by price
        results.sort(key=lambda p: (not p.get("is_featured", False), 
                                   p["sale_price"] if p["is_on_sale"] and p["sale_price"] else p["price"]))
        
        # Apply pagination
        paginated_results = results[offset:offset+limit]
        
        # Enrich with brand and category names
        brands = {b["id"]: b["name"] for b in IN_MEMORY_DB["brands"]}
        categories = {c["id"]: c["name"] for c in IN_MEMORY_DB["categories"]}
        
        for p in paginated_results:
            p["brand_name"] = brands.get(p["brand_id"], "Unknown Brand")
            p["category_name"] = categories.get(p["category_id"], "Unknown Category")
            p["avg_rating"] = 4.5  # Default rating for demo
            p["review_count"] = 10  # Default review count for demo
            
        return paginated_results

    @staticmethod
    async def semantic_search_products(
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Perform semantic search for products using natural language.
        
        Args:
            query: Natural language search query
            filters: Dictionary of filters to apply
            limit: Maximum number of results
            
        Returns:
            List of product dictionaries
        """
        try:
            # Get vector database instance
            vector_db = get_vector_db()
            
            # Perform semantic search
            results = await vector_db.semantic_search(query, limit=limit, filters=filters)
            
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []

    @staticmethod
    async def get_product_by_id(product_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Product details dictionary
        """
        try:
            # Find product with matching ID
            for product in IN_MEMORY_DB["products"]:
                if product["id"] == product_id:
                    result = product.copy()
                    
                    # Add brand and category names
                    for brand in IN_MEMORY_DB["brands"]:
                        if brand["id"] == product["brand_id"]:
                            result["brand_name"] = brand["name"]
                            break
                    
                    for category in IN_MEMORY_DB["categories"]:
                        if category["id"] == product["category_id"]:
                            result["category_name"] = category["name"]
                            break
                    
                    return result
            
            return None
        except Exception as e:
            logger.error(f"Error getting product details: {str(e)}")
            return None

    @staticmethod
    async def check_inventory(product_id: str, size: str, color: str) -> Optional[Dict]:
        """
        Check inventory for a specific product, size, and color.
        
        Args:
            product_id: UUID of the product
            size: Size of the product
            color: Color of the product
            
        Returns:
            Inventory item if found, None otherwise
        """
        try:
            # Find product with matching ID
            for product in IN_MEMORY_DB["products"]:
                if product["id"] == product_id:
                    # Check if size and color exist in attributes
                    if "attributes" not in product:
                        return None
                    
                    attributes = product["attributes"]
                    if "sizes" not in attributes or size not in attributes["sizes"]:
                        return None
                    
                    if "color" not in attributes or color not in attributes["color"]:
                        return None
                    
                    # In real implementation, would check actual inventory here
                    # For demo, return mock inventory data
                    return {
                        "product_id": product_id,
                        "size": size,
                        "color": color,
                        "quantity": 5  # Mock quantity
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error checking inventory: {str(e)}")
            return None

    @staticmethod
    async def get_product_inventory(product_id: str) -> List[Dict]:
        """
        Get inventory information for a product.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            List of inventory items
        """
        sql = """
        SELECT 
            id, product_id, size, color, quantity, location_data
        FROM 
            inventory
        WHERE 
            product_id = $1
        ORDER BY
            size, color
        """
        
        try:
            results = await db.execute_query(sql, product_id)
            return results
        except Exception as e:
            logger.error(f"Error getting product inventory: {str(e)}")
            return []

    @staticmethod
    async def get_product_reviews(product_id: str, limit: int = 5) -> List[Dict]:
        """
        Get reviews for a product.
        
        Args:
            product_id: UUID of the product
            limit: Maximum number of reviews to return
            
        Returns:
            List of review dictionaries
        """
        sql = """
        SELECT 
            id, product_id, customer_name, rating, review_text,
            verified_purchase, metadata, created_at
        FROM 
            reviews
        WHERE 
            product_id = $1
        ORDER BY
            created_at DESC
        LIMIT $2
        """
        
        try:
            results = await db.execute_query(sql, product_id, limit)
            return results
        except Exception as e:
            logger.error(f"Error getting product reviews: {str(e)}")
            return []

    @staticmethod
    async def get_related_products(product_id: str, relation_type: Optional[str] = None) -> List[Dict]:
        """
        Get related products for a product.
        
        Args:
            product_id: UUID of the product
            relation_type: Optional filter for relation type
            
        Returns:
            List of related product dictionaries
        """
        sql = """
        SELECT 
            pr.id AS relation_id,
            pr.relation_type,
            p.id, p.sku, p.name, 
            p.brand_id, b.name as brand_name,
            p.price, p.sale_price, p.is_on_sale
        FROM 
            product_relations pr
        JOIN 
            products p ON pr.related_product_id = p.id
        JOIN 
            brands b ON p.brand_id = b.id
        WHERE 
            pr.product_id = $1
            AND p.is_active = TRUE
        """
        
        params = [product_id]
        
        if relation_type:
            sql += " AND pr.relation_type = $2"
            params.append(relation_type)
        
        sql += " ORDER BY p.is_featured DESC, p.price"
        
        try:
            results = await db.execute_query(sql, *params)
            return results
        except Exception as e:
            logger.error(f"Error getting related products: {str(e)}")
            return []

    @staticmethod
    async def get_category_products(
        category_name: str, 
        include_subcategories: bool = True,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get products in a specific category.
        
        Args:
            category_name: Name of the category
            include_subcategories: Whether to include products from subcategories
            limit: Maximum number of products to return
            
        Returns:
            List of product dictionaries
        """
        # First get the category ID
        category_sql = """
        SELECT id FROM categories WHERE name ILIKE $1
        """
        
        try:
            category_results = await db.execute_query(category_sql, category_name)
            if not category_results:
                return []
            
            category_id = category_results[0]["id"]
            
            # Then get products in this category
            product_sql = """
            SELECT 
                p.id, p.sku, p.name,
                p.brand_id, b.name as brand_name,
                p.category_id, c.name as category_name,
                p.price, p.sale_price, p.is_on_sale,
                p.is_featured
            FROM 
                products p
            JOIN 
                brands b ON p.brand_id = b.id
            JOIN 
                categories c ON p.category_id = c.id
            WHERE 
                p.is_active = TRUE
            """
            
            if include_subcategories:
                product_sql += " AND (p.category_id = $1 OR c.parent_id = $1)"
            else:
                product_sql += " AND p.category_id = $1"
            
            product_sql += """
            ORDER BY 
                p.is_featured DESC,
                CASE WHEN p.is_on_sale THEN p.sale_price ELSE p.price END
            LIMIT $2
            """
            
            results = await db.execute_query(product_sql, category_id, limit)
            return results
        except Exception as e:
            logger.error(f"Error getting category products: {str(e)}")
            return []

    @staticmethod
    async def initialize_vector_db():
        """
        Initialize and index products in the vector database.
        """
        try:
            # Get vector database instance
            vector_db = get_vector_db()
            
            # Index products
            await vector_db.index_products()
            
            logger.info("Vector database initialized and products indexed")
            return True
        except Exception as e:
            logger.error(f"Error initializing vector database: {str(e)}")
            return False

    @staticmethod
    async def get_product_details_complete(product_id: str) -> Dict:
        """
        Get complete product details including inventory, reviews, and related products.
        
        Args:
            product_id: UUID of the product
            
        Returns:
            Complete product details dictionary
        """
        try:
            # Execute queries in parallel
            product, inventory, reviews, related = await asyncio.gather(
                ProductsRepository.get_product_by_id(product_id),
                ProductsRepository.get_product_inventory(product_id),
                ProductsRepository.get_product_reviews(product_id),
                ProductsRepository.get_related_products(product_id)
            )
            
            if not product:
                return {"error": "Product not found"}
                
            # Calculate average rating
            avg_rating = 0
            if reviews:
                avg_rating = sum(review.get("rating", 0) for review in reviews) / len(reviews)
                
            # Add to product details
            product_details = {
                **product,
                "inventory": inventory,
                "reviews": {
                    "count": len(reviews),
                    "average_rating": round(avg_rating, 1),
                    "latest": reviews
                },
                "related_products": related
            }
            
            return product_details
        except Exception as e:
            logger.error(f"Error getting complete product details: {str(e)}")
            return {"error": str(e)}

    # === SQL-BASED REPORTING METHODS ===
    
    @staticmethod
    async def get_inventory_report(
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None
    ) -> Dict:
        """
        Generate inventory report using in-memory data as fallback.
        
        Args:
            category_id: Optional filter by category
            brand_id: Optional filter by brand
            
        Returns:
            Dictionary with inventory report data
        """
        logger.info(f"Generating in-memory inventory report with category_id={category_id}, brand_id={brand_id}")
        
        # Ensure IN_MEMORY_DB is imported and available
        from .db_connection import IN_MEMORY_DB
        
        # Print the structure of IN_MEMORY_DB for debugging
        logger.info(f"IN_MEMORY_DB keys: {list(IN_MEMORY_DB.keys())}")
        logger.info(f"Products count: {len(IN_MEMORY_DB.get('products', []))}")
        logger.info(f"Inventory items count: {len(IN_MEMORY_DB.get('inventory', []))}")
        
        # Get products and inventory data
        products = IN_MEMORY_DB.get("products", []).copy()
        inventory_items = IN_MEMORY_DB.get("inventory", []).copy()
        
        # Create a dictionary for easy product lookup
        product_dict = {p["id"]: p for p in products}
        
        # Filter products
        if category_id is not None:
            products = [p for p in products if p.get("category_id") == category_id]
            product_ids = [p["id"] for p in products]
            inventory_items = [i for i in inventory_items if i.get("product_id") in product_ids]
        
        if brand_id is not None:
            products = [p for p in products if p.get("brand_id") == brand_id]
            product_ids = [p["id"] for p in products]
            inventory_items = [i for i in inventory_items if i.get("product_id") in product_ids]
        
        # Group inventory items by product ID
        inventory_by_product = {}
        for item in inventory_items:
            product_id = item.get("product_id")
            if product_id not in inventory_by_product:
                inventory_by_product[product_id] = []
            inventory_by_product[product_id].append(item)
        
        # Log the filtered products count
        logger.info(f"Filtered products count: {len(products)}")
        logger.info(f"Filtered inventory items count: {len(inventory_items)}")
        
        # Enhance products with brand and category names
        brands = {b["id"]: b["name"] for b in IN_MEMORY_DB.get("brands", [])}
        categories = {c["id"]: c["name"] for c in IN_MEMORY_DB.get("categories", [])}
        
        inventory_data = []
        
        # Include all products that have inventory items
        for product_id, items in inventory_by_product.items():
            if product_id in product_dict:
                product = product_dict[product_id]
                
                # Calculate total quantity for this product across all sizes and colors
                total_quantity = sum(item.get("quantity", 0) for item in items)
                
                # Get unique sizes and colors for this product
                sizes = sorted(list(set(item.get("size") for item in items if item.get("size"))))
                colors = sorted(list(set(item.get("color") for item in items if item.get("color"))))
                
                inventory_data.append({
                    "id": product.get("id", ""),
                    "sku": product.get("sku", ""),
                    "name": product.get("name", "Unknown Product"),
                    "brand": brands.get(product.get("brand_id"), "Unknown"),
                    "category": categories.get(product.get("category_id"), "Unknown"),
                    "price": product.get("price", 0),
                    "sale_price": product.get("sale_price", 0),
                    "is_on_sale": product.get("is_on_sale", False),
                    "available_sizes": sizes,
                    "available_colors": colors,
                    "total_quantity": total_quantity,
                    "discount_percentage": round((product.get("price", 0) - product.get("sale_price", 0)) / product.get("price", 1) * 100, 2) if product.get("is_on_sale") and product.get("sale_price") else 0
                })
        
        # Calculate summary metrics
        total_products = len(inventory_data)
        total_quantity = sum(p.get("total_quantity", 0) for p in inventory_data)
        total_value = sum(p.get("price", 0) * p.get("total_quantity", 1) for p in inventory_data)
        discounted_value = sum((p.get("sale_price", p.get("price", 0)) if p.get("is_on_sale") and p.get("sale_price") else p.get("price", 0)) * p.get("total_quantity", 1) for p in inventory_data)
        total_discount = total_value - discounted_value
        
        # Group by brand
        brand_summary = {}
        for product in inventory_data:
            brand = product.get("brand", "Unknown")
            if brand not in brand_summary:
                brand_summary[brand] = {
                    "count": 0,
                    "total_quantity": 0,
                    "total_value": 0,
                    "discounted_value": 0
                }
            
            brand_summary[brand]["count"] += 1
            brand_summary[brand]["total_quantity"] += product.get("total_quantity", 0)
            brand_summary[brand]["total_value"] += product.get("price", 0) * product.get("total_quantity", 1)
            brand_summary[brand]["discounted_value"] += (product.get("sale_price", 0) if product.get("is_on_sale") and product.get("sale_price") else product.get("price", 0)) * product.get("total_quantity", 1)
        
        # Group by category
        category_summary = {}
        for product in inventory_data:
            category = product.get("category", "Unknown")
            if category not in category_summary:
                category_summary[category] = {
                    "count": 0,
                    "total_quantity": 0,
                    "total_value": 0,
                    "discounted_value": 0
                }
            
            category_summary[category]["count"] += 1
            category_summary[category]["total_quantity"] += product.get("total_quantity", 0)
            category_summary[category]["total_value"] += product.get("price", 0) * product.get("total_quantity", 1)
            category_summary[category]["discounted_value"] += (product.get("sale_price", 0) if product.get("is_on_sale") and product.get("sale_price") else product.get("price", 0)) * product.get("total_quantity", 1)
        
        logger.info(f"Generated report with {total_products} products and {total_quantity} total items")
        
        return {
            "total_products": total_products,
            "total_quantity": total_quantity,
            "total_value": total_value,
            "discounted_value": discounted_value,
            "total_discount": total_discount,
            "brand_summary": brand_summary,
            "category_summary": category_summary,
            "inventory_data": inventory_data
        }
    
    @staticmethod
    async def get_price_analysis_report(
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict:
        """
        Generate a price analysis report using SQL queries.
        This demonstrates using SQL for analytics rather than semantic search.
        
        Args:
            category_id: Optional filter by category
            min_price: Optional minimum price
            max_price: Optional maximum price
            
        Returns:
            Dictionary with price analysis report data
        """
        try:
            # For Supportly's in-memory implementation, we'll directly use the fallback
            # since the SQL query isn't fully supported
            logger.info(f"Generating price analysis report with category_id={category_id}, min_price={min_price}, max_price={max_price}")
            
            # Skip SQL attempt and go straight to in-memory implementation
            return ProductsRepository._generate_in_memory_price_analysis(category_id, min_price, max_price)
            
            # This SQL implementation is kept for reference but not used in the current version
            """
            # Base SQL for price analysis
            sql = '''
            WITH price_stats AS (
                SELECT 
                    category_id,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY price) as median_price,
                    COUNT(*) as product_count,
                    COUNT(CASE WHEN is_on_sale THEN 1 END) as sale_count,
                    AVG(CASE WHEN is_on_sale THEN (price - sale_price) / price * 100 ELSE 0 END) as avg_discount
                FROM 
                    products
                WHERE 
                    is_active = TRUE
            '''
            
            params = []
            param_count = 0
            
            # Add filters
            where_added = False
            
            if category_id is not None:
                sql += " AND category_id = $1"
                params.append(category_id)
                where_added = True
                param_count += 1
            
            if min_price is not None:
                param_count += 1
                sql += f" AND price >= ${param_count}"
                params.append(min_price)
                where_added = True
            
            if max_price is not None:
                param_count += 1
                sql += f" AND price <= ${param_count}"
                params.append(max_price)
                where_added = True
            
            # Complete the CTE and join with categories
            sql += '''
                GROUP BY category_id
            )
            SELECT 
                c.name as category_name,
                ps.avg_price,
                ps.min_price,
                ps.max_price,
                ps.median_price,
                ps.product_count,
                ps.sale_count,
                ps.avg_discount
            FROM 
                price_stats ps
            JOIN 
                categories c ON ps.category_id = c.id
            ORDER BY 
                c.name
            '''
            
            try:
                # Execute query
                price_data = await db.execute_query(sql, *params)
            except Exception as e:
                logger.error(f"SQL error in price analysis report: {str(e)}")
                # Fallback to in-memory implementation
                return ProductsRepository._generate_in_memory_price_analysis(category_id, min_price, max_price)
            
            # Calculate overall stats
            total_products = sum(row["product_count"] for row in price_data)
            total_on_sale = sum(row["sale_count"] for row in price_data)
            avg_price = sum(row["avg_price"] * row["product_count"] for row in price_data) / total_products if total_products > 0 else 0
            avg_discount = sum(row["avg_discount"] * row["sale_count"] for row in price_data) / total_on_sale if total_on_sale > 0 else 0
            
            return {
                "total_products": total_products,
                "total_on_sale": total_on_sale,
                "percent_on_sale": round(total_on_sale / total_products * 100, 2) if total_products > 0 else 0,
                "overall_avg_price": round(avg_price, 2),
                "overall_avg_discount": round(avg_discount, 2),
                "price_data": price_data
            }
            """
            
        except Exception as e:
            logger.error(f"Error generating price analysis report: {str(e)}")
            return {
                "error": str(e),
                "total_products": 0,
                "total_on_sale": 0,
                "percent_on_sale": 0,
                "overall_avg_price": 0,
                "overall_avg_discount": 0,
                "price_data": []
            }
    
    @staticmethod
    def _generate_in_memory_price_analysis(
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Dict:
        """
        Generate price analysis report using in-memory data as fallback.
        
        Args:
            category_id: Optional filter by category
            min_price: Optional minimum price
            max_price: Optional maximum price
            
        Returns:
            Dictionary with price analysis report data
        """
        logger.info(f"Generating in-memory price analysis with category_id={category_id}, min_price={min_price}, max_price={max_price}")
        
        # Ensure IN_MEMORY_DB is imported and available
        from .db_connection import IN_MEMORY_DB
        
        # Log the database state for debugging
        logger.info(f"IN_MEMORY_DB keys: {list(IN_MEMORY_DB.keys())}")
        logger.info(f"Products count: {len(IN_MEMORY_DB.get('products', []))}")
        
        # Filter products
        products = IN_MEMORY_DB.get("products", []).copy()
        
        if category_id is not None:
            products = [p for p in products if p.get("category_id") == category_id]
        
        if min_price is not None:
            products = [p for p in products if p.get("price", 0) >= min_price]
        
        if max_price is not None:
            products = [p for p in products if p.get("price", 0) <= max_price]
        
        # Log filtered count
        logger.info(f"Filtered products count: {len(products)}")
        
        # Get categories
        categories = {c["id"]: c["name"] for c in IN_MEMORY_DB.get("categories", [])}
        
        # Group by category
        category_data = {}
        for product in products:
            cat_id = product.get("category_id")
            if cat_id is None:
                continue
                
            cat_name = categories.get(cat_id, f"Category {cat_id}")
            
            if cat_name not in category_data:
                category_data[cat_name] = {
                    "prices": [],
                    "sale_prices": [],
                    "discounts": [],
                    "product_count": 0,
                    "sale_count": 0
                }
            
            price = product.get("price", 0)
            is_on_sale = product.get("is_on_sale", False)
            sale_price = product.get("sale_price", 0) if is_on_sale else price
            
            category_data[cat_name]["prices"].append(price)
            category_data[cat_name]["product_count"] += 1
            
            if is_on_sale:
                discount_pct = (price - sale_price) / price * 100 if price > 0 else 0
                category_data[cat_name]["sale_prices"].append(sale_price)
                category_data[cat_name]["discounts"].append(discount_pct)
                category_data[cat_name]["sale_count"] += 1
        
        # Calculate statistics for each category
        price_data = []
        total_products = 0
        total_on_sale = 0
        weighted_avg_price_sum = 0
        weighted_avg_discount_sum = 0
        
        for cat_name, data in category_data.items():
            prices = data["prices"]
            if not prices:
                continue
                
            prices.sort()  # For median calculation
            product_count = data["product_count"]
            sale_count = data["sale_count"]
            
            # Basic statistics
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # Calculate median
            if len(prices) % 2 == 0:
                median_price = (prices[len(prices)//2 - 1] + prices[len(prices)//2]) / 2
            else:
                median_price = prices[len(prices)//2]
                
            # Calculate average discount
            avg_discount = sum(data["discounts"]) / len(data["discounts"]) if data["discounts"] else 0
            
            price_data.append({
                "category_name": cat_name,
                "avg_price": round(avg_price, 2),
                "min_price": min_price,
                "max_price": max_price,
                "median_price": round(median_price, 2),
                "product_count": product_count,
                "sale_count": sale_count,
                "avg_discount": round(avg_discount, 2)
            })
            
            total_products += product_count
            total_on_sale += sale_count
            weighted_avg_price_sum += avg_price * product_count
            weighted_avg_discount_sum += avg_discount * sale_count
        
        # Sort by category name
        price_data.sort(key=lambda x: x["category_name"])
        
        # Calculate overall stats
        overall_avg_price = weighted_avg_price_sum / total_products if total_products > 0 else 0
        overall_avg_discount = weighted_avg_discount_sum / total_on_sale if total_on_sale > 0 else 0
        
        logger.info(f"Generated price analysis with {total_products} products across {len(price_data)} categories")
        
        return {
            "total_products": total_products,
            "total_on_sale": total_on_sale,
            "percent_on_sale": round(total_on_sale / total_products * 100, 2) if total_products > 0 else 0,
            "overall_avg_price": round(overall_avg_price, 2),
            "overall_avg_discount": round(overall_avg_discount, 2),
            "price_data": price_data
        }

# Add missing import at the top
import asyncio 