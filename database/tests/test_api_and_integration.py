#!/usr/bin/env python
"""
Test cases for the products API endpoints and integration functionality.
Tests that API endpoints correctly interact with the products agent and repository.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from database.api import products_router
from database.integration import ProductsToolIntegration, setup_products_integration
from database.products_agent import ProductsAgent
from database.products_repository import ProductsRepository


class TestProductsAPI(unittest.TestCase):
    """Test cases for the Products API endpoints."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a FastAPI app for testing
        self.app = FastAPI()
        self.app.include_router(products_router)
        self.client = TestClient(self.app)
        
        # Sample product data
        self.sample_product = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Nike Air Max 270",
            "brand_name": "Nike",
            "price": 150.00,
            "sale_price": 129.99,
            "is_on_sale": True
        }
        
        # Sample response for search endpoint
        self.sample_search_response = {
            "results": [self.sample_product],
            "response": "Here are some products that match your search for 'Nike running shoes'"
        }
        
        # Sample response for details endpoint
        self.sample_details_response = {
            "details": {
                **self.sample_product,
                "inventory": [
                    {"size": "10", "color": "White", "quantity": 5}
                ]
            },
            "response": "# Nike Air Max 270\n**Brand**: Nike | **Category**: Running"
        }
        
        # Sample response for availability endpoint
        self.sample_availability_response = {
            "available": True,
            "product": self.sample_product,
            "inventory": {"size": "10", "color": "White", "quantity": 5},
            "response": "Great news! The Nike Air Max 270 is available in size 10 and color White."
        }
        
        # Sample response for category endpoint
        self.sample_category_response = {
            "products": [self.sample_product],
            "response": "Here are some popular products in the 'Running' category"
        }

    @patch.object(ProductsAgent, 'search_products')
    def test_search_products_endpoint(self, mock_search_products):
        """Test the search products API endpoint."""
        # Configure the mock
        mock_search_products.return_value = self.sample_search_response
        
        # Test request data
        request_data = {"query": "Nike running shoes"}
        
        # Make the POST request to the endpoint
        response = self.client.post("/products/search", json=request_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("response", response_data)
        self.assertIn("data", response_data)
        self.assertIn("results", response_data["data"])
        
        # Verify mock was called with expected parameters
        mock_search_products.assert_awaited_once_with("Nike running shoes")

    @patch.object(ProductsAgent, 'get_product_details')
    def test_get_product_details_endpoint(self, mock_get_product_details):
        """Test the get product details API endpoint."""
        # Configure the mock
        mock_get_product_details.return_value = self.sample_details_response
        
        # Test request data
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        request_data = {"product_id": product_id}
        
        # Make the POST request to the endpoint
        response = self.client.post("/products/details", json=request_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("response", response_data)
        self.assertIn("data", response_data)
        self.assertIn("details", response_data["data"])
        
        # Verify mock was called with expected parameters
        mock_get_product_details.assert_awaited_once_with(product_id)

    @patch.object(ProductsAgent, 'check_product_availability')
    def test_check_product_availability_endpoint(self, mock_check_availability):
        """Test the check product availability API endpoint."""
        # Configure the mock
        mock_check_availability.return_value = self.sample_availability_response
        
        # Test request data
        request_data = {
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "size": "10",
            "color": "White"
        }
        
        # Make the POST request to the endpoint
        response = self.client.post("/products/availability", json=request_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("response", response_data)
        self.assertIn("data", response_data)
        self.assertIn("available", response_data["data"])
        self.assertIn("product", response_data["data"])
        self.assertIn("inventory", response_data["data"])
        
        # Verify mock was called with expected parameters
        mock_check_availability.assert_awaited_once_with(
            request_data["product_id"], 
            request_data["size"], 
            request_data["color"]
        )

    @patch.object(ProductsAgent, 'get_category_products')
    def test_get_category_products_endpoint(self, mock_get_category_products):
        """Test the get category products API endpoint."""
        # Configure the mock
        mock_get_category_products.return_value = self.sample_category_response
        
        # Test request data
        request_data = {"category_name": "Running"}
        
        # Make the POST request to the endpoint
        response = self.client.post("/products/category", json=request_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("response", response_data)
        self.assertIn("data", response_data)
        self.assertIn("products", response_data["data"])
        
        # Verify mock was called with expected parameters
        mock_get_category_products.assert_awaited_once_with("Running")

    @patch.object(ProductsRepository, 'search_products')
    def test_raw_search_products_endpoint(self, mock_search_products):
        """Test the raw search products API endpoint."""
        # Configure the mock
        mock_search_products.return_value = [self.sample_product]
        
        # Make the GET request to the endpoint with query parameters
        response = self.client.get("/products/raw/search?query=Nike&price_min=100&price_max=200&size=10&color=White")
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["name"], "Nike Air Max 270")
        
        # Verify mock was called with expected parameters
        mock_search_products.assert_awaited_once()
        args, kwargs = mock_search_products.call_args
        self.assertEqual(kwargs["query"], "Nike")
        self.assertEqual(kwargs["price_min"], 100.0)
        self.assertEqual(kwargs["price_max"], 200.0)
        self.assertEqual(kwargs["size"], "10")
        self.assertEqual(kwargs["color"], "White")

    @patch.object(ProductsRepository, 'get_product_details_complete')
    def test_raw_get_product_details_endpoint(self, mock_get_product_details):
        """Test the raw get product details API endpoint."""
        # Configure the mock
        mock_get_product_details.return_value = {**self.sample_product, "inventory": []}
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Make the GET request to the endpoint
        response = self.client.get(f"/products/raw/product/{product_id}")
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["id"], product_id)
        self.assertEqual(response_data["name"], "Nike Air Max 270")
        
        # Verify mock was called with expected parameters
        mock_get_product_details.assert_awaited_once_with(product_id)
        
        # Test with error response
        mock_get_product_details.return_value = {"error": "Product not found"}
        
        # Make the GET request to the endpoint
        response = self.client.get("/products/raw/product/nonexistent-id")
        
        # Assertions
        self.assertEqual(response.status_code, 404)

    @patch.object(ProductsRepository, 'get_category_products')
    def test_raw_get_category_products_endpoint(self, mock_get_category_products):
        """Test the raw get category products API endpoint."""
        # Configure the mock
        mock_get_category_products.return_value = [self.sample_product]
        
        # Test category name
        category_name = "Running"
        
        # Make the GET request to the endpoint
        response = self.client.get(f"/products/raw/categories/{category_name}/products")
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["name"], "Nike Air Max 270")
        
        # Verify mock was called with expected parameters
        mock_get_category_products.assert_awaited_once()
        args, kwargs = mock_get_category_products.call_args
        self.assertEqual(kwargs["category_name"], category_name)
        self.assertEqual(kwargs["include_subcategories"], True)


class TestProductsIntegration(unittest.TestCase):
    """Test cases for the Products integration with the application."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a FastAPI app for testing
        self.app = FastAPI()
        
        # Mock register_tool method
        self.app.register_tool = MagicMock()
        
        # Sample tool description
        self.sample_tool_description = {
            "name": "products_tool",
            "description": "Use this tool to search for shoes",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "details", "availability", "category"]
                    }
                },
                "required": ["action"]
            }
        }
        
        # Sample tool execution result
        self.sample_tool_result = {
            "results": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Nike Air Max 270"
                }
            ],
            "response": "Here are some Nike shoes"
        }

    @patch('database.products_tool.get_tool_description')
    @patch.object(ProductsToolIntegration, 'register_with_app')
    async def test_setup_products_integration(
        self, 
        mock_register_with_app,
        mock_get_tool_description
    ):
        """Test setting up the products integration with the application."""
        # Configure the mocks
        mock_get_tool_description.return_value = self.sample_tool_description
        
        # Call the setup function
        integration = await setup_products_integration(self.app)
        
        # Assertions
        self.assertIsInstance(integration, ProductsToolIntegration)
        
        # Verify register_with_app was called
        mock_register_with_app.assert_awaited_once()
        
        # Since we mocked the app.include_router method, it should have been called if available
        # This is tested in the class method test below

    @patch('database.products_tool.get_tool_description')
    @patch('database.products_tool.ProductsTool.execute')
    async def test_integration_register_with_app(
        self, 
        mock_execute,
        mock_get_tool_description
    ):
        """Test registering the products tool with the application."""
        # Configure the mocks
        mock_get_tool_description.return_value = self.sample_tool_description
        mock_execute.return_value = self.sample_tool_result
        
        # Create the integration
        integration = ProductsToolIntegration()
        
        # Create a mock register_tool function
        mock_register_tool = MagicMock()
        
        # Call the register_with_app method
        await integration.register_with_app(mock_register_tool)
        
        # Verify register_tool was called with the tool description and a callable
        mock_register_tool.assert_called_once()
        args, kwargs = mock_register_tool.call_args
        self.assertEqual(args[0], self.sample_tool_description)
        self.assertTrue(callable(args[1]))
        
        # Test the executor function by calling it with parameters
        tool_params = {"action": "search", "query": "Nike shoes"}
        executor_fn = args[1]
        result = await executor_fn(tool_params)
        
        # Verify the tool.execute method was called with the correct parameters
        mock_execute.assert_awaited_once_with("search", query="Nike shoes")
        
        # Verify the result is as expected
        self.assertEqual(result, self.sample_tool_result)
        
        # Test the executor function with missing action
        tool_params_no_action = {"query": "Nike shoes"}
        result = await executor_fn(tool_params_no_action)
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("response", result)
        self.assertIn("No action specified", result["error"])

    @patch('database.products_tool.get_tool_description')
    @patch('database.api.products_router')
    async def test_setup_class_method(
        self, 
        mock_products_router,
        mock_get_tool_description
    ):
        """Test the setup class method of the integration."""
        # Configure the mocks
        mock_get_tool_description.return_value = self.sample_tool_description
        
        # Call the setup class method
        integration = await ProductsToolIntegration.setup(self.app)
        
        # Assertions
        self.assertIsInstance(integration, ProductsToolIntegration)
        
        # Verify register_tool was called
        self.app.register_tool.assert_called_once()
        
        # Create app with include_router instead of register_tool
        app_with_router = FastAPI()
        app_with_router.include_router = MagicMock()
        
        # Call the setup class method with the new app
        integration = await ProductsToolIntegration.setup(app_with_router)
        
        # Verify include_router was called
        app_with_router.include_router.assert_called_once()


def run_async_test(coro):
    """Helper function to run async tests."""
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main() 