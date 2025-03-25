#!/usr/bin/env python
"""
Test cases for the products agent functionality.
Tests the core features of the products agent including:
- Product search
- Product details
- Product availability
- Category browsing
"""

import os
import sys
import asyncio
import unittest
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.products_agent import ProductsAgent
from database.products_repository import ProductsRepository
from chat_models import ChatHistory, ChatMessage


class TestProductsAgent(unittest.TestCase):
    """Test cases for the ProductsAgent class."""

    def setUp(self):
        """Set up test environment before each test."""
        self.agent = ProductsAgent()
        
        # Create a simple chat history
        self.chat_history = ChatHistory(messages=[])
        
        # Create sample product data
        self.sample_product = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "sku": "NIKE-AIR-001",
            "name": "Nike Air Max 270",
            "description": "The Nike Air Max 270 delivers unrivaled cushioning and style.",
            "brand_id": 1,
            "brand_name": "Nike",
            "category_id": 2,
            "category_name": "Running",
            "price": 150.00,
            "sale_price": 129.99,
            "is_on_sale": True,
            "is_featured": True,
            "is_active": True,
            "attributes": {
                "weight": "10.5 oz",
                "style": "CW7306-100",
                "material": "Mesh, Synthetic"
            },
            "images": [
                "https://example.com/images/nike-air-max-270-1.jpg",
                "https://example.com/images/nike-air-max-270-2.jpg"
            ],
            "metadata": {
                "release_date": "2022-03-15",
                "popularity_score": 4.8
            }
        }
        
        # Sample inventory data
        self.sample_inventory = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "size": "10",
                "color": "White",
                "quantity": 5,
                "location_data": {"warehouse": "Main", "shelf": "A12"}
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "size": "9",
                "color": "Black",
                "quantity": 3,
                "location_data": {"warehouse": "Main", "shelf": "A13"}
            }
        ]
        
        # Sample reviews data
        self.sample_reviews = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174010",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_name": "John Doe",
                "rating": 5,
                "review_text": "Best running shoes I've ever owned!",
                "verified_purchase": True,
                "metadata": {"date": "2022-04-10"},
                "created_at": "2022-04-10T10:30:00Z"
            }
        ]
        
        # Sample search results
        self.sample_search_results = [self.sample_product]
        
        # Sample category products
        self.sample_category_products = [self.sample_product]
        
        # Sample complete product details including inventory, reviews, and related products
        self.sample_complete_product = {
            **self.sample_product,
            "inventory": self.sample_inventory,
            "reviews": {
                "count": 1,
                "average_rating": 5.0,
                "latest": self.sample_reviews
            },
            "related_products": [
                {
                    "id": "223e4567-e89b-12d3-a456-426614174000",
                    "sku": "NIKE-AIR-002",
                    "name": "Nike Air Max 90",
                    "brand_id": 1,
                    "brand_name": "Nike",
                    "price": 140.00,
                    "sale_price": None,
                    "is_on_sale": False,
                    "relation_type": "similar"
                }
            ]
        }

    @patch.object(ProductsRepository, 'search_products')
    async def test_search_products(self, mock_search_products):
        """Test searching for products."""
        # Configure the mock
        mock_search_products.return_value = self.sample_search_results
        
        # Test search query
        search_query = "Nike running shoes"
        
        # Call the method being tested
        result = await self.agent.search_products(search_query)
        
        # Assertions
        self.assertIn("results", result)
        self.assertIn("response", result)
        self.assertEqual(result["results"], self.sample_search_results)
        self.assertIsInstance(result["response"], str)
        self.assertIn("Nike Air Max 270", result["response"])
        
        # Verify mock was called with expected parameters
        mock_search_products.assert_called_once()
        args, kwargs = mock_search_products.call_args
        self.assertIn("query", kwargs)

    @patch.object(ProductsRepository, 'get_product_details_complete')
    async def test_get_product_details(self, mock_get_product_details):
        """Test getting detailed product information."""
        # Configure the mock
        mock_get_product_details.return_value = self.sample_complete_product
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        result = await self.agent.get_product_details(product_id)
        
        # Assertions
        self.assertIn("details", result)
        self.assertIn("response", result)
        self.assertEqual(result["details"], self.sample_complete_product)
        self.assertIsInstance(result["response"], str)
        self.assertIn("Nike Air Max 270", result["response"])
        self.assertIn("White", result["response"])
        self.assertIn("Black", result["response"])
        
        # Verify mock was called with expected parameters
        mock_get_product_details.assert_called_once_with(product_id)

    @patch.object(ProductsRepository, 'get_product_by_id')
    @patch.object(ProductsRepository, 'check_inventory')
    async def test_check_product_availability(self, mock_check_inventory, mock_get_product_by_id):
        """Test checking product availability."""
        # Configure the mocks
        mock_get_product_by_id.return_value = self.sample_product
        mock_check_inventory.return_value = self.sample_inventory[0]
        
        # Test parameters
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        size = "10"
        color = "White"
        
        # Call the method being tested
        result = await self.agent.check_product_availability(product_id, size, color)
        
        # Assertions
        self.assertIn("product", result)
        self.assertIn("inventory", result)
        self.assertIn("available", result)
        self.assertIn("response", result)
        self.assertEqual(result["product"], self.sample_product)
        self.assertEqual(result["inventory"], self.sample_inventory[0])
        self.assertTrue(result["available"])
        self.assertIsInstance(result["response"], str)
        self.assertIn("available", result["response"].lower())
        
        # Verify mocks were called with expected parameters
        mock_get_product_by_id.assert_called_once_with(product_id)
        mock_check_inventory.assert_called_once_with(product_id, size, color)

    @patch.object(ProductsRepository, 'check_inventory')
    @patch.object(ProductsRepository, 'get_product_by_id')
    async def test_check_product_not_available(self, mock_get_product_by_id, mock_check_inventory):
        """Test checking product that is not available."""
        # Configure the mocks
        mock_get_product_by_id.return_value = self.sample_product
        # Return inventory with zero quantity
        not_available_inventory = dict(self.sample_inventory[0])
        not_available_inventory["quantity"] = 0
        mock_check_inventory.return_value = not_available_inventory
        
        # Test parameters
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        size = "10"
        color = "White"
        
        # Call the method being tested
        result = await self.agent.check_product_availability(product_id, size, color)
        
        # Assertions
        self.assertFalse(result["available"])
        self.assertIn("out of stock", result["response"].lower())

    @patch.object(ProductsRepository, 'get_category_products')
    async def test_get_category_products(self, mock_get_category_products):
        """Test getting products in a category."""
        # Configure the mock
        mock_get_category_products.return_value = self.sample_category_products
        
        # Test category name
        category_name = "Running"
        
        # Call the method being tested
        result = await self.agent.get_category_products(category_name)
        
        # Assertions
        self.assertIn("products", result)
        self.assertIn("response", result)
        self.assertEqual(result["products"], self.sample_category_products)
        self.assertIsInstance(result["response"], str)
        self.assertIn("Running", result["response"])
        self.assertIn("Nike Air Max 270", result["response"])
        
        # Verify mock was called with expected parameters
        mock_get_category_products.assert_called_once()
        args, kwargs = mock_get_category_products.call_args
        self.assertEqual(kwargs["category_name"], category_name)
        self.assertTrue(kwargs["include_subcategories"])

    def test_extract_search_params(self):
        """Test extracting search parameters from natural language queries."""
        # Test with brand
        params = self.agent._extract_search_params("Show me Nike running shoes")
        self.assertIn("query", params)
        self.assertEqual(params["query"], "Show me Nike running shoes")
        
        # Test with price range
        params = self.agent._extract_search_params("Running shoes between $100 and $200")
        self.assertIn("price_min", params)
        self.assertIn("price_max", params)
        self.assertEqual(params["price_min"], 100.0)
        self.assertEqual(params["price_max"], 200.0)
        
        # Test with color
        params = self.agent._extract_search_params("Red shoes")
        self.assertIn("query", params)
        self.assertEqual(params["query"], "Red shoes")
        
        # Test with size
        params = self.agent._extract_search_params("Size 10 basketball shoes")
        self.assertIn("query", params)
        self.assertIn("size", params)
        self.assertEqual(params["size"], "10")
        
        # Test with brand and color
        params = self.agent._extract_search_params("Nike shoes in red color")
        self.assertIn("query", params)
        self.assertEqual(params["query"], "Nike shoes in red color")

    def test_format_search_response(self):
        """Test formatting search results into a natural language response."""
        # Test with results
        response = self.agent._format_search_response(
            self.sample_search_results,
            {"query": "Nike running shoes"},
            "Nike running shoes"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("Nike Air Max 270", response)
        self.assertIn("Nike", response)
        
        # Test with no results
        response = self.agent._format_search_response(
            [],
            {"query": "Some rare shoes that don't exist"},
            "Some rare shoes that don't exist"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("I'm sorry", response.lower())

    def test_format_product_details_response(self):
        """Test formatting product details into a natural language response."""
        # Test with full product details
        response = self.agent._format_product_details_response(self.sample_complete_product)
        
        self.assertIsInstance(response, str)
        self.assertIn("Nike Air Max 270", response)
        self.assertIn("Nike", response)
        self.assertIn("$129.99", response)
        self.assertIn("Running", response)
        self.assertIn("White", response)
        self.assertIn("Black", response)
        self.assertIn("10", response)
        self.assertIn("9", response)
        
        # Test with error
        response = self.agent._format_product_details_response({"error": "Product not found"})
        
        self.assertIsInstance(response, str)
        self.assertIn("I'm sorry", response.lower())
        self.assertIn("product not found", response.lower())

    def test_format_availability_response(self):
        """Test formatting availability information into a natural language response."""
        # Test with available product
        response = self.agent._format_availability_response(
            self.sample_product,
            self.sample_inventory[0],
            "10",
            "White"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("available", response.lower())
        self.assertIn("Nike Air Max 270", response)
        
        # Test with out of stock product
        not_available = dict(self.sample_inventory[0])
        not_available["quantity"] = 0
        
        response = self.agent._format_availability_response(
            self.sample_product,
            not_available,
            "10",
            "White"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("out of stock", response.lower())
        
        # Test with product not available in that size/color
        response = self.agent._format_availability_response(
            self.sample_product,
            None,
            "11",
            "Red"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("not available", response.lower())

    def test_format_category_products_response(self):
        """Test formatting category products into a natural language response."""
        # Test with products
        response = self.agent._format_category_products_response(
            self.sample_category_products,
            "Running"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("Running", response)
        self.assertIn("Nike Air Max 270", response)
        
        # Test with no products
        response = self.agent._format_category_products_response(
            [],
            "Some category with no products"
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("I'm sorry", response.lower())
        self.assertIn("couldn't find any products", response.lower())


def run_async_test(coro):
    """Helper function to run async tests."""
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main() 