#!/usr/bin/env python
"""
Test cases for the products repository functionality.
Tests the database queries with mocked database connections.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.products_repository import ProductsRepository
from database.db_connection import db


class TestProductsRepository(unittest.TestCase):
    """Test cases for the ProductsRepository class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Sample product data
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
        
        # Sample related products
        self.sample_related_products = [
            {
                "id": "223e4567-e89b-12d3-a456-426614174000",
                "relation_id": "123e4567-e89b-12d3-a456-426614174100",
                "relation_type": "similar",
                "sku": "NIKE-AIR-002",
                "name": "Nike Air Max 90",
                "brand_id": 1,
                "brand_name": "Nike",
                "price": 140.00,
                "sale_price": None,
                "is_on_sale": False
            }
        ]
        
        # Category data
        self.sample_category = {
            "id": 2,
            "name": "Running",
            "parent_id": 1
        }

    @patch.object(db, 'execute_query')
    async def test_search_products(self, mock_execute_query):
        """Test searching for products."""
        # Configure the mock
        mock_execute_query.return_value = [self.sample_product]
        
        # Test search parameters
        query = "Nike running shoes"
        
        # Call the method being tested
        results = await ProductsRepository.search_products(query=query)
        
        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.sample_product)
        
        # Verify mock was called
        mock_execute_query.assert_called_once()
        
        # Test with additional parameters
        await ProductsRepository.search_products(
            query=query,
            category_id=2,
            brand_id=1,
            price_min=100,
            price_max=200,
            size="10",
            color="White"
        )
        
        # Verify mock was called again
        self.assertEqual(mock_execute_query.call_count, 2)

    @patch.object(db, 'execute_query')
    async def test_get_product_by_id(self, mock_execute_query):
        """Test getting a product by ID."""
        # Configure the mock
        mock_execute_query.return_value = [self.sample_product]
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        result = await ProductsRepository.get_product_by_id(product_id)
        
        # Assertions
        self.assertEqual(result, self.sample_product)
        
        # Verify mock was called with expected parameters
        mock_execute_query.assert_called_once()
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)
        
        # Test with product not found
        mock_execute_query.return_value = []
        
        # Call the method again
        result = await ProductsRepository.get_product_by_id("nonexistent-id")
        
        # Assertions
        self.assertIsNone(result)

    @patch.object(db, 'execute_query')
    async def test_get_product_inventory(self, mock_execute_query):
        """Test getting inventory for a product."""
        # Configure the mock
        mock_execute_query.return_value = self.sample_inventory
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        results = await ProductsRepository.get_product_inventory(product_id)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results, self.sample_inventory)
        
        # Verify mock was called with expected parameters
        mock_execute_query.assert_called_once()
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)

    @patch.object(db, 'execute_query')
    async def test_get_product_reviews(self, mock_execute_query):
        """Test getting reviews for a product."""
        # Configure the mock
        mock_execute_query.return_value = self.sample_reviews
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        results = await ProductsRepository.get_product_reviews(product_id)
        
        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(results, self.sample_reviews)
        
        # Verify mock was called with expected parameters
        mock_execute_query.assert_called_once()
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)

    @patch.object(db, 'execute_query')
    async def test_get_related_products(self, mock_execute_query):
        """Test getting related products."""
        # Configure the mock
        mock_execute_query.return_value = self.sample_related_products
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        results = await ProductsRepository.get_related_products(product_id)
        
        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(results, self.sample_related_products)
        
        # Verify mock was called with expected parameters
        mock_execute_query.assert_called_once()
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)
        
        # Test with relation type
        await ProductsRepository.get_related_products(product_id, relation_type="similar")
        
        # Verify mock was called again with both parameters
        self.assertEqual(mock_execute_query.call_count, 2)
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)
        self.assertTrue("similar" in args)

    @patch.object(db, 'execute_query')
    async def test_check_inventory(self, mock_execute_query):
        """Test checking inventory for a specific product variant."""
        # Configure the mock
        mock_execute_query.return_value = [self.sample_inventory[0]]
        
        # Test parameters
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        size = "10"
        color = "White"
        
        # Call the method being tested
        result = await ProductsRepository.check_inventory(product_id, size, color)
        
        # Assertions
        self.assertEqual(result, self.sample_inventory[0])
        
        # Verify mock was called with expected parameters
        mock_execute_query.assert_called_once()
        args, kwargs = mock_execute_query.call_args
        self.assertTrue(product_id in args)
        self.assertTrue(size in args)
        self.assertTrue(color in args)
        
        # Test with inventory not found
        mock_execute_query.return_value = []
        
        # Call the method again
        result = await ProductsRepository.check_inventory(product_id, "999", "Purple")
        
        # Assertions
        self.assertIsNone(result)

    @patch.object(db, 'execute_query')
    async def test_get_category_products(self, mock_execute_query):
        """Test getting products in a category."""
        # First mock call returns the category
        mock_execute_query.side_effect = [
            [self.sample_category],  # First call: get category ID
            [self.sample_product]     # Second call: get products
        ]
        
        # Test parameters
        category_name = "Running"
        include_subcategories = True
        limit = 10
        
        # Call the method being tested
        results = await ProductsRepository.get_category_products(
            category_name,
            include_subcategories,
            limit
        )
        
        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], self.sample_product)
        
        # Verify mock was called twice (once for category, once for products)
        self.assertEqual(mock_execute_query.call_count, 2)
        
        # Verify first call arguments (category lookup)
        first_call_args, first_call_kwargs = mock_execute_query.call_args_list[0]
        self.assertTrue(category_name in first_call_args)
        
        # Verify second call arguments (products query)
        second_call_args, second_call_kwargs = mock_execute_query.call_args_list[1]
        self.assertEqual(len(second_call_args), 2)  # category_id and limit
        self.assertEqual(second_call_args[0], self.sample_category["id"])
        self.assertEqual(second_call_args[1], limit)

    @patch.object(ProductsRepository, 'get_product_by_id')
    @patch.object(ProductsRepository, 'get_product_inventory')
    @patch.object(ProductsRepository, 'get_product_reviews')
    @patch.object(ProductsRepository, 'get_related_products')
    async def test_get_product_details_complete(
        self, 
        mock_get_related_products,
        mock_get_product_reviews,
        mock_get_product_inventory,
        mock_get_product_by_id
    ):
        """Test getting complete product details."""
        # Configure the mocks
        mock_get_product_by_id.return_value = self.sample_product
        mock_get_product_inventory.return_value = self.sample_inventory
        mock_get_product_reviews.return_value = self.sample_reviews
        mock_get_related_products.return_value = self.sample_related_products
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method being tested
        result = await ProductsRepository.get_product_details_complete(product_id)
        
        # Assertions
        self.assertIn("id", result)
        self.assertEqual(result["id"], product_id)
        self.assertIn("inventory", result)
        self.assertEqual(result["inventory"], self.sample_inventory)
        self.assertIn("reviews", result)
        self.assertEqual(result["reviews"]["latest"], self.sample_reviews)
        self.assertIn("related_products", result)
        self.assertEqual(result["related_products"], self.sample_related_products)
        
        # Verify all mocks were called with the product ID
        mock_get_product_by_id.assert_called_once_with(product_id)
        mock_get_product_inventory.assert_called_once_with(product_id)
        mock_get_product_reviews.assert_called_once_with(product_id)
        mock_get_related_products.assert_called_once_with(product_id)
        
        # Test with product not found
        mock_get_product_by_id.return_value = None
        
        # Call the method again
        result = await ProductsRepository.get_product_details_complete("nonexistent-id")
        
        # Assertions
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Product not found")

    @patch.object(db, 'execute_query')
    async def test_search_products_exception(self, mock_execute_query):
        """Test exception handling in search_products."""
        # Configure the mock to raise an exception
        mock_execute_query.side_effect = Exception("Database error")
        
        # Call the method being tested
        results = await ProductsRepository.search_products(query="test")
        
        # Assertions
        self.assertEqual(results, [])
        
        # Verify mock was called
        mock_execute_query.assert_called_once()


def run_async_test(coro):
    """Helper function to run async tests."""
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main() 