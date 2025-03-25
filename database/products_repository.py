#!/usr/bin/env python
"""
Repository module for product database operations.
This module contains all the database queries for products.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from .db_connection import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        offset: int = 0
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
            
        Returns:
            List of product dictionaries
        """
        # Base query using the materialized view for efficient search
        sql = """
        SELECT ps.id, ps.sku, ps.name, ps.description, 
               ps.brand_name, ps.category_name, 
               ps.price, ps.sale_price, ps.is_on_sale, 
               ps.is_featured, ps.is_active,
               ps.attributes, ps.images, ps.inventory,
               ps.avg_rating, ps.review_count
        FROM product_search ps
        WHERE ps.is_active = TRUE
        """
        
        params = []
        param_index = 1
        
        # Add text search condition if query is provided
        if query:
            sql += f" AND (ps.name ILIKE ${param_index} OR ps.description ILIKE ${param_index})"
            params.append(f"%{query}%")
            param_index += 1
        
        # Add category filter
        if category_id is not None:
            sql += f" AND (c.id = ${param_index} OR c.parent_id = ${param_index})"
            params.append(category_id)
            param_index += 1
        
        # Add brand filter
        if brand_id is not None:
            sql += f" AND ps.brand_id = ${param_index}"
            params.append(brand_id)
            param_index += 1
        
        # Add price range filters
        if price_min is not None:
            sql += f" AND (CASE WHEN ps.is_on_sale THEN ps.sale_price ELSE ps.price END) >= ${param_index}"
            params.append(price_min)
            param_index += 1
        
        if price_max is not None:
            sql += f" AND (CASE WHEN ps.is_on_sale THEN ps.sale_price ELSE ps.price END) <= ${param_index}"
            params.append(price_max)
            param_index += 1
            
        # Add inventory filters (size and color)
        # These are more complex because they're in JSONB array
        if size is not None or color is not None:
            sql += " AND ps.inventory @> ("
            inventory_conditions = []
            
            if size is not None:
                inventory_conditions.append(f"'size': '${param_index}'")
                params.append(size)
                param_index += 1
                
            if color is not None:
                inventory_conditions.append(f"'color': '${param_index}'")
                params.append(color)
                param_index += 1
                
            sql += "{" + ", ".join(inventory_conditions) + "}"
            sql += ")::jsonb"
        
        # Add sorting (featured products first, then by rating and price)
        sql += """
        ORDER BY 
            ps.is_featured DESC,
            ps.avg_rating DESC,
            CASE WHEN ps.is_on_sale THEN ps.sale_price ELSE ps.price END
        """
        
        # Add pagination
        sql += f" LIMIT ${param_index} OFFSET ${param_index+1}"
        params.extend([limit, offset])
        
        try:
            results = await db.execute_query(sql, *params)
            return results
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
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
        sql = """
        SELECT 
            p.id, p.sku, p.name, p.description,
            p.brand_id, b.name as brand_name,
            p.category_id, c.name as category_name,
            p.price, p.sale_price, p.is_on_sale,
            p.is_featured, p.is_active,
            p.attributes, p.images, p.metadata
        FROM 
            products p
        JOIN 
            brands b ON p.brand_id = b.id
        JOIN 
            categories c ON p.category_id = c.id
        WHERE 
            p.id = $1
            AND p.is_active = TRUE
        """
        
        try:
            results = await db.execute_query(sql, product_id)
            if not results:
                return None
            return results[0]
        except Exception as e:
            logger.error(f"Error getting product details: {str(e)}")
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
    async def check_inventory(product_id: str, size: str, color: str) -> Optional[Dict]:
        """
        Check inventory for a specific product variant.
        
        Args:
            product_id: UUID of the product
            size: Size of the product
            color: Color of the product
            
        Returns:
            Inventory information or None if not found
        """
        sql = """
        SELECT 
            id, product_id, size, color, quantity, location_data
        FROM 
            inventory
        WHERE 
            product_id = $1
            AND size = $2
            AND color ILIKE $3
        """
        
        try:
            results = await db.execute_query(sql, product_id, size, color)
            if not results:
                return None
            return results[0]
        except Exception as e:
            logger.error(f"Error checking inventory: {str(e)}")
            return None

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

# Add missing import at the top
import asyncio 