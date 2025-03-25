#!/usr/bin/env python
"""
Test cases for the integration with the main Supportly application.
Tests how the products functionality integrates with the OrchestratorAgent.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Try to import the necessary modules, but don't fail if they're not available
# This allows the test to be discovered even if the main application is not available
try:
    from agents.orchestrator_agent import OrchestratorAgent
    from agents.products_agent import ProductsAgent as MainProductsAgent
    from database.products_agent import ProductsAgent as DBProductsAgent
    from chat_models import ChatMessage, ChatHistory
    MAIN_APP_AVAILABLE = True
except ImportError:
    MAIN_APP_AVAILABLE = False

# Skip the entire test class if the main application is not available
@unittest.skipIf(not MAIN_APP_AVAILABLE, "Main application modules not available")
class TestMainApplicationIntegration(unittest.TestCase):
    """Test cases for integration with the main Supportly application."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a mock OrchestratorAgent
        self.orchestrator = MagicMock(spec=OrchestratorAgent)
        self.orchestrator.knowledge_agent = MagicMock()
        self.orchestrator.greeting_agent = MagicMock()
        self.orchestrator.orders_agent = MagicMock()
        self.orchestrator.products_agent = MagicMock(spec=MainProductsAgent)
        
        # Set up the downstream agents dictionary
        self.orchestrator.downstream_agents = {
            'initial_greeting': self.orchestrator.greeting_agent,
            'knowledge': self.orchestrator.knowledge_agent,
            'greeting': self.orchestrator.greeting_agent,
            'orders': self.orchestrator.orders_agent,
            'products': self.orchestrator.products_agent,
            'other': self.orchestrator.knowledge_agent
        }
        
        # Create a mock ChatMessage and ChatHistory
        self.message = MagicMock(spec=ChatMessage)
        self.message.message = "Show me Nike running shoes"
        self.message.conversation_id = "test-conversation-id"
        
        self.chat_history = MagicMock(spec=ChatHistory)
        self.chat_history.messages = []
        
        # Sample product data for mock responses
        self.sample_product = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Nike Air Max 270",
            "brand_name": "Nike",
            "price": 150.00,
            "sale_price": 129.99,
            "is_on_sale": True
        }
        
        # Sample response for the products agent
        self.sample_agent_response = ChatMessage(
            message="Here are some Nike running shoes: Nike Air Max 270, Nike ZoomX, and more.",
            conversation_id="test-conversation-id",
            sender="ai",
            suggestions=["Tell me more about Nike Air Max 270", "Show me more products", "Do you have any running shoes?"],
            created_at="2023-03-25T12:00:00Z"
        )

    @patch.object(OrchestratorAgent, '_classify_intent')
    @patch.object(MainProductsAgent, 'process_message')
    async def test_products_intent_routing(self, mock_process_message, mock_classify_intent):
        """Test routing to the products agent when products intent is detected."""
        # Configure the mocks
        mock_classify_intent.return_value = 'products'
        mock_process_message.return_value = self.sample_agent_response
        
        # Create a real orchestrator for this test
        orchestrator = OrchestratorAgent()
        orchestrator.products_agent = MagicMock(spec=MainProductsAgent)
        orchestrator.products_agent.process_message = mock_process_message
        
        # Set up the downstream agents dictionary
        orchestrator.downstream_agents = {
            'products': orchestrator.products_agent,
            # Add other agents as needed
        }
        
        # Call the method being tested
        result = await orchestrator.process_message(self.message, self.chat_history)
        
        # Assertions
        self.assertEqual(result.message, self.sample_agent_response.message)
        self.assertEqual(result.conversation_id, self.sample_agent_response.conversation_id)
        self.assertEqual(result.suggestions, self.sample_agent_response.suggestions)
        
        # Verify the intent classification was called
        mock_classify_intent.assert_awaited_once_with(self.message.message, self.chat_history)
        
        # Verify the products agent was called
        mock_process_message.assert_awaited_once_with(self.message, self.chat_history)

    @patch.object(DBProductsAgent, 'search_products')
    async def test_db_products_agent_integration(self, mock_search_products):
        """Test interaction between MainProductsAgent and DBProductsAgent."""
        # Skip test if MainProductsAgent is not available
        if not MAIN_APP_AVAILABLE:
            self.skipTest("MainProductsAgent not available")
        
        # Configure the mocks
        mock_search_products.return_value = {
            "results": [self.sample_product],
            "response": "Here are some products that match your search for 'Nike running shoes'"
        }
        
        # Create instances of both agents
        db_agent = DBProductsAgent()
        main_agent = MainProductsAgent()
        
        # Replace the main agent's products_tool with a mock that calls our db_agent
        main_agent.products_tool = MagicMock()
        main_agent.products_tool.execute = AsyncMock()
        main_agent.products_tool.execute.return_value = {
            "results": [self.sample_product],
            "response": "Here are some products that match your search for 'Nike running shoes'"
        }
        
        # Initialize the agents
        main_agent.initialize()
        
        # Create test message and history
        message = ChatMessage(
            message="Show me Nike running shoes",
            conversation_id="test-conversation-id",
            sender="user"
        )
        history = ChatHistory(messages=[])
        
        # Call the main agent's process_message
        result = await main_agent.process_message(message, history)
        
        # Assertions
        self.assertIsInstance(result, ChatMessage)
        self.assertIn("Nike", result.message)
        
        # Verify the products_tool.execute method was called (indirectly)
        self.assertTrue(main_agent.products_tool.execute.called)

    @patch('database.integration.ProductsToolIntegration.register_with_app')
    async def test_app_startup_integration(self, mock_register_with_app):
        """Test the integration during application startup."""
        # Skip test if main app is not available
        if not MAIN_APP_AVAILABLE:
            self.skipTest("Main application not available")
        
        # Import the necessary modules for testing startup
        from fastapi import FastAPI
        from api import startup_event, setup_products_integration, get_orchestrator
        
        # Create a mock app
        app = MagicMock(spec=FastAPI)
        app.register_tool = AsyncMock()
        app.include_router = MagicMock()
        
        # Create a mock for get_orchestrator
        get_orchestrator_mock = MagicMock(return_value=self.orchestrator)
        
        # Create a mock for setup_products_integration
        setup_products_integration_mock = AsyncMock()
        
        # Patch the relevant functions
        with patch('api.get_orchestrator', get_orchestrator_mock):
            with patch('api.setup_products_integration', setup_products_integration_mock):
                # Call the startup event
                await startup_event()
                
                # Verify the orchestrator was initialized
                get_orchestrator_mock.assert_called_once()
                
                # Verify the products integration was set up
                setup_products_integration_mock.assert_awaited_once()


def run_async_test(coro):
    """Helper function to run async tests."""
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main() 