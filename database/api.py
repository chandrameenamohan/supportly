#!/usr/bin/env python
"""
API endpoints for the products database and agent functionality.
This module provides routes for interacting with the shoe product database.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .products_agent import ProductsAgent
from .products_repository import ProductsRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the router
products_router = APIRouter(prefix="/products", tags=["products"])

# Pydantic models for request/response validation
class ProductSearchRequest(BaseModel):
    """Request model for product search"""
    query: str
    
class ProductDetailsRequest(BaseModel):
    """Request model for product details"""
    product_id: str
    
class AvailabilityRequest(BaseModel):
    """Request model for checking product availability"""
    product_id: str
    size: str
    color: str
    
class CategoryProductsRequest(BaseModel):
    """Request model for getting products in a category"""
    category_name: str

class AgentResponse(BaseModel):
    """Response model with formatted text and data"""
    response: str
    data: Dict

# Dependency to get the products agent
async def get_products_agent():
    """Dependency to create and provide a products agent."""
    agent = ProductsAgent()
    return agent

@products_router.post("/search", response_model=AgentResponse)
async def search_products(
    request: ProductSearchRequest,
    agent: ProductsAgent = Depends(get_products_agent)
):
    """
    Search for products based on a natural language query.
    
    Args:
        request: Search request with query
        agent: Products agent dependency
        
    Returns:
        Agent response with formatted text and data
    """
    try:
        result = await agent.search_products(request.query)
        return {
            "response": result["response"],
            "data": {"results": result["results"]}
        }
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")

@products_router.post("/details", response_model=AgentResponse)
async def get_product_details(
    request: ProductDetailsRequest,
    agent: ProductsAgent = Depends(get_products_agent)
):
    """
    Get detailed information about a product.
    
    Args:
        request: Product details request with product ID
        agent: Products agent dependency
        
    Returns:
        Agent response with formatted text and data
    """
    try:
        result = await agent.get_product_details(request.product_id)
        return {
            "response": result["response"],
            "data": {"details": result.get("details", {})}
        }
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting product details: {str(e)}")

@products_router.post("/availability", response_model=AgentResponse)
async def check_product_availability(
    request: AvailabilityRequest,
    agent: ProductsAgent = Depends(get_products_agent)
):
    """
    Check if a product is available in a specific size and color.
    
    Args:
        request: Availability request with product ID, size, and color
        agent: Products agent dependency
        
    Returns:
        Agent response with formatted text and data
    """
    try:
        result = await agent.check_product_availability(
            request.product_id, request.size, request.color
        )
        return {
            "response": result["response"],
            "data": {
                "available": result["available"],
                "product": result.get("product", {}),
                "inventory": result.get("inventory", {})
            }
        }
    except Exception as e:
        logger.error(f"Error checking product availability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking product availability: {str(e)}")

@products_router.post("/category", response_model=AgentResponse)
async def get_category_products(
    request: CategoryProductsRequest,
    agent: ProductsAgent = Depends(get_products_agent)
):
    """
    Get products in a specific category.
    
    Args:
        request: Category products request with category name
        agent: Products agent dependency
        
    Returns:
        Agent response with formatted text and data
    """
    try:
        result = await agent.get_category_products(request.category_name)
        return {
            "response": result["response"],
            "data": {"products": result.get("products", [])}
        }
    except Exception as e:
        logger.error(f"Error getting category products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting category products: {str(e)}")

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