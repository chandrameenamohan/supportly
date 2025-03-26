#!/usr/bin/env python
"""
API endpoints for the products database and agent functionality.
This module provides routes for interacting with the shoe product database.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path, FastAPI
from pydantic import BaseModel, Field

from .products_agent import ProductsAgent
from .products_repository import ProductsRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the router
products_router = APIRouter(prefix="/products", tags=["products"])
api_router = APIRouter()

# Pydantic models for request/response validation
class ProductSearchRequest(BaseModel):
    """Request model for product search"""
    query: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    size: Optional[str] = None
    color: Optional[str] = None
    limit: int = 10
    offset: int = 0
    use_semantic_search: bool = True

class SemanticSearchRequest(BaseModel):
    """Request model for semantic product search"""
    query: str
    filters: Optional[Dict] = None
    limit: int = 10

class ProductSearchResponse(BaseModel):
    """Response model for product search"""
    results: List[Dict]
    total_count: int
    query: Optional[str] = None

class ProductDetailsRequest(BaseModel):
    """Request model for product details"""
    product_id: str

class ProductDetailsResponse(BaseModel):
    """Response model for product details"""
    details: Dict

class ProductAvailabilityRequest(BaseModel):
    """Request model for product availability"""
    product_id: str
    size: str
    color: str

class ProductAvailabilityResponse(BaseModel):
    """Response model for product availability"""
    available: bool
    inventory: Optional[Dict] = None
    product: Optional[Dict] = None

class CategoryProductsRequest(BaseModel):
    """Request model for category products"""
    category_name: str
    include_subcategories: bool = True
    limit: int = 10

class CategoryProductsResponse(BaseModel):
    """Response model for category products"""
    products: List[Dict]
    category_name: str

class AgentResponse(BaseModel):
    """Response model with formatted text and data"""
    response: str
    data: Dict

class ProductDetailResponse(BaseModel):
    """Response for product details"""
    id: str
    name: str
    description: str
    brand_name: str
    category_name: str
    price: float
    sale_price: Optional[float] = None
    is_on_sale: bool
    attributes: Dict

class InventoryReportRequest(BaseModel):
    """Request model for generating inventory reports via SQL queries"""
    category_id: Optional[int] = None
    brand_id: Optional[int] = None

class InventoryReport(APIRouter):
    """API endpoint for generating detailed inventory reports using SQL"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_api_route(
            "/inventory",
            self.generate_inventory_report,
            methods=["POST"],
            response_model=Dict,
            description="Generate a detailed inventory report using SQL queries"
        )
    
    async def generate_inventory_report(self, request: InventoryReportRequest):
        """Generate a detailed inventory report using SQL queries"""
        try:
            logger.info(f"Generating inventory report with params: {request}")
            result = await ProductsRepository.get_inventory_report(
                category_id=request.category_id,
                brand_id=request.brand_id
            )
            return result
        except Exception as e:
            logger.error(f"Error generating inventory report: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating inventory report: {str(e)}"
            )

class PriceAnalysisRequest(BaseModel):
    """Request model for generating price analysis reports via SQL queries"""
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

class PriceAnalysis(APIRouter):
    """API endpoint for generating price analysis reports using SQL"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_api_route(
            "/price-analysis",
            self.generate_price_analysis,
            methods=["POST"],
            response_model=Dict,
            description="Generate a price analysis report using SQL queries"
        )
    
    async def generate_price_analysis(self, request: PriceAnalysisRequest):
        """Generate a price analysis report using SQL queries"""
        try:
            logger.info(f"Generating price analysis with params: {request}")
            result = await ProductsRepository.get_price_analysis_report(
                category_id=request.category_id,
                min_price=request.min_price,
                max_price=request.max_price
            )
            return result
        except Exception as e:
            logger.error(f"Error generating price analysis: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating price analysis: {str(e)}"
            )

# Dependency to get the products agent
async def get_products_agent():
    """Dependency to create and provide a products agent."""
    agent = ProductsAgent()
    return agent

@products_router.post("/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """
    Search for products with filters.
    """
    try:
        results = await ProductsRepository.search_products(
            query=request.query,
            category_id=request.category_id,
            brand_id=request.brand_id,
            price_min=request.price_min,
            price_max=request.price_max,
            size=request.size,
            color=request.color,
            limit=request.limit,
            offset=request.offset,
            use_semantic_search=request.use_semantic_search
        )
        
        return {
            "results": results,
            "total_count": len(results),
            "query": request.query
        }
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@products_router.post("/semantic-search", response_model=ProductSearchResponse)
async def semantic_search_products(request: SemanticSearchRequest):
    """
    Perform semantic search for products based on natural language.
    """
    try:
        results = await ProductsRepository.semantic_search_products(
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        
        return {
            "results": results,
            "total_count": len(results),
            "query": request.query
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in semantic search: {str(e)}")

@products_router.post("/details", response_model=ProductDetailsResponse)
async def get_product_details(request: ProductDetailsRequest):
    """
    Get detailed information about a product.
    """
    try:
        details = await ProductsRepository.get_product_by_id(request.product_id)
        if not details:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting product details: {str(e)}")

@products_router.post("/availability", response_model=ProductAvailabilityResponse)
async def check_product_availability(request: ProductAvailabilityRequest):
    """
    Check if a product is available in a specific size and color.
    """
    try:
        product = await ProductsRepository.get_product_by_id(request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        inventory = await ProductsRepository.check_inventory(
            product_id=request.product_id,
            size=request.size,
            color=request.color
        )
        
        available = inventory is not None and inventory.get("quantity", 0) > 0
        
        return {
            "available": available,
            "inventory": inventory,
            "product": product
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking product availability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking product availability: {str(e)}")

@products_router.post("/category", response_model=CategoryProductsResponse)
async def get_category_products(request: CategoryProductsRequest):
    """
    Get products in a specific category.
    """
    try:
        products = await ProductsRepository.get_category_products(
            category_name=request.category_name,
            include_subcategories=request.include_subcategories,
            limit=request.limit
        )
        
        return {
            "products": products,
            "category_name": request.category_name
        }
    except Exception as e:
        logger.error(f"Error getting category products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting category products: {str(e)}")

@products_router.post("/initialize-vector-db")
async def initialize_vector_db():
    """
    Initialize and index products in the vector database.
    """
    try:
        success = await ProductsRepository.initialize_vector_db()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to initialize vector database")
        
        return {"status": "Vector database initialized successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing vector database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error initializing vector database: {str(e)}")

# Natural language search endpoint that uses ProductsAgent
@products_router.post("/natural-search")
async def natural_language_search(query: str):
    """
    Search products using natural language understanding.
    """
    try:
        agent = ProductsAgent()
        response = await agent.search_products(query)
        return response
    except Exception as e:
        logger.error(f"Error in natural language search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in natural language search: {str(e)}")

@products_router.get("/raw/search", response_model=List[Dict])
async def raw_search_products(
    query: Optional[str] = None,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Direct access to the product search functionality.
    This endpoint bypasses the agent and provides raw access to the repository.
    
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
    try:
        results = await ProductsRepository.search_products(
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
        return results
    except Exception as e:
        logger.error(f"Error in raw product search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in raw product search: {str(e)}")

@products_router.get("/raw/product/{product_id}", response_model=Dict)
async def raw_get_product_details(product_id: str):
    """
    Direct access to get product details.
    This endpoint bypasses the agent and provides raw access to the repository.
    
    Args:
        product_id: UUID of the product
        
    Returns:
        Product details dictionary
    """
    try:
        result = await ProductsRepository.get_product_details_complete(product_id)
        if not result or "error" in result:
            raise HTTPException(status_code=404, detail="Product not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in raw product details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in raw product details: {str(e)}")

@products_router.get("/raw/categories/{category_name}/products", response_model=List[Dict])
async def raw_get_category_products(
    category_name: str,
    include_subcategories: bool = True,
    limit: int = Query(10, ge=1, le=100)
):
    """
    Direct access to get products in a category.
    This endpoint bypasses the agent and provides raw access to the repository.
    
    Args:
        category_name: Name of the category
        include_subcategories: Whether to include products from subcategories
        limit: Maximum number of products to return
        
    Returns:
        List of product dictionaries
    """
    try:
        results = await ProductsRepository.get_category_products(
            category_name=category_name,
            include_subcategories=include_subcategories,
            limit=limit
        )
        return results
    except Exception as e:
        logger.error(f"Error in raw category products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in raw category products: {str(e)}")

@products_router.get("/details/{product_id}", response_model=ProductDetailResponse)
async def get_product_details(product_id: str):
    """
    Get detailed information about a specific product.
    """
    try:
        product = await ProductsRepository.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting product details: {str(e)}")

@products_router.get("/reports/most-discounted", response_model=List[Dict])
async def get_most_discounted_products(limit: int = 5, category_id: Optional[int] = None):
    """
    Get the most discounted products, optionally filtered by category.
    This endpoint demonstrates SQL's ability to perform complex sorting and filtering.
    """
    try:
        # SQL query for most discounted products
        sql = """
        SELECT 
            p.id, p.sku, p.name,
            b.name as brand_name,
            c.name as category_name,
            p.price, p.sale_price,
            (p.price - p.sale_price) / p.price * 100 as discount_percentage
        FROM 
            products p
        JOIN 
            brands b ON p.brand_id = b.id
        JOIN 
            categories c ON p.category_id = c.id
        WHERE 
            p.is_active = TRUE
            AND p.is_on_sale = TRUE
            AND p.sale_price IS NOT NULL
        """
        
        params = []
        param_count = 0
        
        # Add category filter if provided
        if category_id is not None:
            param_count += 1
            sql += f" AND p.category_id = ${param_count}"
            params.append(category_id)
        
        # Add sorting and limit
        sql += """
        ORDER BY 
            discount_percentage DESC
        """
        
        param_count += 1
        sql += f" LIMIT ${param_count}"
        params.append(limit)
        
        # Execute query
        from .db_connection import db
        try:
            results = await db.execute_query(sql, *params)
            
            # If SQL fails, use in-memory fallback
            if not results:
                # In-memory fallback
                products = [p for p in ProductsRepository.IN_MEMORY_DB["products"] 
                          if p["is_on_sale"] and p["sale_price"] is not None]
                
                # Add discount percentage
                for p in products:
                    p["discount_percentage"] = (p["price"] - p["sale_price"]) / p["price"] * 100
                
                # Filter by category if needed
                if category_id is not None:
                    products = [p for p in products if p["category_id"] == category_id]
                
                # Sort by discount percentage
                products.sort(key=lambda x: x["discount_percentage"], reverse=True)
                
                # Apply limit
                results = products[:limit]
                
                # Add brand and category names
                brands = {b["id"]: b["name"] for b in ProductsRepository.IN_MEMORY_DB["brands"]}
                categories = {c["id"]: c["name"] for c in ProductsRepository.IN_MEMORY_DB["categories"]}
                
                for p in results:
                    p["brand_name"] = brands.get(p["brand_id"], "Unknown")
                    p["category_name"] = categories.get(p["category_id"], "Unknown")
            
            return results
            
        except Exception as e:
            logger.error(f"SQL error in most discounted products query: {str(e)}")
            # Fallback using in-memory data
            products = [p for p in ProductsRepository.IN_MEMORY_DB["products"] 
                      if p["is_on_sale"] and p["sale_price"] is not None]
            
            # Add discount percentage
            for p in products:
                p["discount_percentage"] = (p["price"] - p["sale_price"]) / p["price"] * 100
            
            # Filter by category if needed
            if category_id is not None:
                products = [p for p in products if p["category_id"] == category_id]
            
            # Sort by discount percentage
            products.sort(key=lambda x: x["discount_percentage"], reverse=True)
            
            # Apply limit
            results = products[:limit]
            
            # Add brand and category names
            brands = {b["id"]: b["name"] for b in ProductsRepository.IN_MEMORY_DB["brands"]}
            categories = {c["id"]: c["name"] for c in ProductsRepository.IN_MEMORY_DB["categories"]}
            
            for p in results:
                p["brand_name"] = brands.get(p["brand_id"], "Unknown")
                p["category_name"] = categories.get(p["category_id"], "Unknown")
            
            return results
        
    except Exception as e:
        logger.error(f"Error getting most discounted products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting most discounted products: {str(e)}")

def init_api_routes(app: FastAPI):
    """Initialize all API routes"""
    # Register the main API router
    app.include_router(api_router, prefix="/api")
    
    # Register database product endpoints
    app.include_router(products_router, prefix="/api/products")
    
    # Register report endpoints
    inventory_report = InventoryReport(prefix="/reports", tags=["reports"])
    price_analysis = PriceAnalysis(prefix="/reports", tags=["reports"])
    
    # Include the report routers in the products router
    products_router.include_router(inventory_report)
    products_router.include_router(price_analysis) 