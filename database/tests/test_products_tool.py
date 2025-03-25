#!/usr/bin/env python
"""
Test cases for the products tool functionality.
Tests the integration between the products agent and the tool used by the chatbot.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.products_tool import ProductsTool, get_tool_description
from database.products_agent import ProductsAgent


class TestProductsTool(unittest.TestCase):
    """Test cases for the ProductsTool class."""

    def setUp(self):
        """Set up test environment before each test."""
        self.tool = ProductsTool()
        
        # Sample search response from agent
        self.sample_search_response = {
            "results": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Nike Air Max 270",
                    "brand_name": "Nike",
                    "price": 150.0,
                    "sale_price": 129.99,
                    "is_on_sale": True
                }
            ],
            "response": "Here are some products that match your search for 'Nike running shoes':\n1. **Nike Air Max 270** by Nike - $129.99"
        }
        
        # Sample product details response
        self.sample_details_response = {
            "details": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Nike Air Max 270",
                "brand_name": "Nike",
                "price": 150.0,
                "sale_price": 129.99,
                "is_on_sale": True,
                "inventory": [
                    {"size": "10", "color": "White", "quantity": 5},
                    {"size": "9", "color": "Black", "quantity": 3}
                ]
            },
            "response": "# Nike Air Max 270\n**Brand**: Nike | **Category**: Running\n**Price**: $129.99 ($150.00 - 13% off)"
        }
        
        # Sample availability response
        self.sample_availability_response = {
            "product": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Nike Air Max 270"
            },
            "inventory": {
                "size": "10",
                "color": "White",
                "quantity": 5
            },
            "available": True,
            "response": "Great news! The Nike Air Max 270 is available in size 10 and color White. Would you like to add it to your cart?"
        }
        
        # Sample out of stock response
        self.sample_out_of_stock_response = {
            "product": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Nike Air Max 270"
            },
            "inventory": {
                "size": "10",
                "color": "White",
                "quantity": 0
            },
            "available": False,
            "response": "I'm sorry, the Nike Air Max 270 in size 10 and color White is currently out of stock. Would you like to check other sizes or colors?"
        }
        
        # Sample category response
        self.sample_category_response = {
            "products": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Nike Air Max 270",
                    "brand_name": "Nike",
                    "price": 150.0,
                    "sale_price": 129.99,
                    "is_on_sale": True
                }
            ],
            "response": "Here are some popular products in the 'Running' category:\n1. **Nike Air Max 270** by Nike - $129.99"
        }

    @patch.object(ProductsAgent, 'search_products')
    async def test_search_products_action(self, mock_search_products):
        """Test the search action of the products tool."""
        # Configure the mock
        mock_search_products.return_value = self.sample_search_response
        
        # Execute the search action
        result = await self.tool.execute("search", query="Nike running shoes")
        
        # Assertions
        self.assertEqual(result, self.sample_search_response)
        self.assertIn("response", result)
        self.assertIn("results", result)
        
        # Verify the agent method was called with correct parameters
        mock_search_products.assert_called_once_with("Nike running shoes")

    @patch.object(ProductsAgent, 'search_products')
    async def test_search_with_empty_query(self, mock_search_products):
        """Test the search action with an empty query."""
        # Execute the search action with empty query
        result = await self.tool.execute("search", query="")
        
        # Assertions
        self.assertIn("error", result)
        self.assertIn("response", result)
        self.assertIn("need to know what kind of shoes", result["response"])
        
        # Verify the agent method was not called
        mock_search_products.assert_not_called()

    @patch.object(ProductsAgent, 'get_product_details')
    async def test_details_action(self, mock_get_product_details):
        """Test the details action of the products tool."""
        # Configure the mock
        mock_get_product_details.return_value = self.sample_details_response
        
        # Test product ID
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Execute the details action
        result = await self.tool.execute("details", product_id=product_id)
        
        # Assertions
        self.assertEqual(result, self.sample_details_response)
        self.assertIn("response", result)
        self.assertIn("details", result)
        
        # Verify the agent method was called with correct parameters
        mock_get_product_details.assert_called_once_with(product_id)

    @patch.object(ProductsAgent, 'get_product_details')
    async def test_details_with_empty_product_id(self, mock_get_product_details):
        """Test the details action with an empty product ID."""
        # Execute the details action with empty product ID
        result = await self.tool.execute("details", product_id="")
        
        # Assertions
        self.assertIn("error", result)
        self.assertIn("response", result)
        self.assertIn("need a product ID", result["response"])
        
        # Verify the agent method was not called
        mock_get_product_details.assert_not_called()

    @patch.object(ProductsAgent, 'check_product_availability')
    async def test_availability_action(self, mock_check_availability):
        """Test the availability action of the products tool."""
        # Configure the mock
        mock_check_availability.return_value = self.sample_availability_response
        
        # Test parameters
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        size = "10"
        color = "White"
        
        # Execute the availability action
        result = await self.tool.execute("availability", product_id=product_id, size=size, color=color)
        
        # Assertions
        self.assertEqual(result, self.sample_availability_response)
        self.assertIn("response", result)
        self.assertIn("available", result)
        self.assertTrue(result["available"])
        
        # Verify the agent method was called with correct parameters
        mock_check_availability.assert_called_once_with(product_id, size, color)

    @patch.object(ProductsAgent, 'check_product_availability')
    async def test_out_of_stock_availability(self, mock_check_availability):
        """Test the availability action for out of stock products."""
        # Configure the mock
        mock_check_availability.return_value = self.sample_out_of_stock_response
        
        # Test parameters
        product_id = "123e4567-e89b-12d3-a456-426614174000"
        size = "10"
        color = "White"
        
        # Execute the availability action
        result = await self.tool.execute("availability", product_id=product_id, size=size, color=color)
        
        # Assertions
        self.assertEqual(result, self.sample_out_of_stock_response)
        self.assertIn("response", result)
        self.assertIn("available", result)
        self.assertFalse(result["available"])
        
        # Verify the agent method was called with correct parameters
        mock_check_availability.assert_called_once_with(product_id, size, color)

    async def test_availability_with_missing_parameters(self):
        """Test the availability action with missing parameters."""
        # Test with missing product ID
        result = await self.tool.execute("availability", product_id="", size="10", color="White")
        self.assertIn("error", result)
        self.assertIn("need a product ID", result["response"])
        
        # Test with missing size
        result = await self.tool.execute("availability", product_id="123", size="", color="White")
        self.assertIn("error", result)
        self.assertIn("need to know which size", result["response"])
        
        # Test with missing color
        result = await self.tool.execute("availability", product_id="123", size="10", color="")
        self.assertIn("error", result)
        self.assertIn("need to know which color", result["response"])

    @patch.object(ProductsAgent, 'get_category_products')
    async def test_category_action(self, mock_get_category_products):
        """Test the category action of the products tool."""
        # Configure the mock
        mock_get_category_products.return_value = self.sample_category_response
        
        # Test category name
        category_name = "Running"
        
        # Execute the category action
        result = await self.tool.execute("category", category_name=category_name)
        
        # Assertions
        self.assertEqual(result, self.sample_category_response)
        self.assertIn("response", result)
        self.assertIn("products", result)
        
        # Verify the agent method was called with correct parameters
        mock_get_category_products.assert_called_once_with(category_name)

    @patch.object(ProductsAgent, 'get_category_products')
    async def test_category_with_empty_name(self, mock_get_category_products):
        """Test the category action with an empty category name."""
        # Execute the category action with empty category name
        result = await self.tool.execute("category", category_name="")
        
        # Assertions
        self.assertIn("error", result)
        self.assertIn("response", result)
        self.assertIn("need to know which category", result["response"])
        
        # Verify the agent method was not called
        mock_get_category_products.assert_not_called()

    async def test_unknown_action(self):
        """Test executing an unknown action."""
        # Execute an unknown action
        result = await self.tool.execute("unknown_action")
        
        # Assertions
        self.assertIn("error", result)
        self.assertIn("response", result)
        self.assertIn("I don't know how to perform the action", result["response"])

    def test_get_tool_description(self):
        """Test the get_tool_description function."""
        # Get the tool description
        description = get_tool_description()
        
        # Assertions
        self.assertIsInstance(description, dict)
        self.assertIn("name", description)
        self.assertIn("description", description)
        self.assertIn("parameters", description)
        
        # Check the parameters
        parameters = description["parameters"]
        self.assertIn("properties", parameters)
        self.assertIn("required", parameters)
        
        # Check the action property
        properties = parameters["properties"]
        self.assertIn("action", properties)
        self.assertEqual(properties["action"]["type"], "string")
        self.assertIn("enum", properties["action"])
        
        # Check that all supported actions are included
        supported_actions = properties["action"]["enum"]
        self.assertIn("search", supported_actions)
        self.assertIn("details", supported_actions)
        self.assertIn("availability", supported_actions)
        self.assertIn("category", supported_actions)


def run_async_test(coro):
    """Helper function to run async tests."""
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main() 