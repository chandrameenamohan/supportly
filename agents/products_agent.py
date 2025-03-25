from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from textwrap import dedent
from utils import utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR
import logging
import json
import traceback
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

class ProductsAgent(BaseAgent):
    """
    The products agent is responsible for providing information about the products.
    Integrates with the products database to provide accurate and up-to-date information.
    """
    agent_name: str = "products"

    def __init__(self):
        super().__init__()
        self.llm = None
        self.products_tool = None

    def initialize(self):
        """Initialize the products agent with LLM and database tool"""
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)
        
        # Try to import the products tool
        try:
            from database.products_tool import ProductsTool
            self.products_tool = ProductsTool()
            logger.info("Products tool initialized successfully")
        except ImportError:
            logger.warning("Products tool not available, running in limited mode")
            self.products_tool = None

    async def _execute_tool_action(self, action: str, **kwargs) -> dict:
        """
        Execute an action with the products tool.
        
        Args:
            action: The action to execute
            **kwargs: Additional parameters for the action
            
        Returns:
            The result of the action
        """
        if not self.products_tool:
            return {
                "error": "Products database not available",
                "response": "I'm sorry, but I don't have access to our product database at the moment. Please try again later."
            }
        
        try:
            # Execute the action with the products tool
            result = await self.products_tool.execute(action, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing products tool action: {str(e)}\n{traceback.format_exc()}")
            return {
                "error": str(e),
                "response": "I encountered an error while trying to get information from our product database. Please try again later."
            }

    async def _extract_tool_parameters(self, message: str, chat_history: ChatHistory) -> dict:
        """
        Extract parameters for the products tool from the user's message.
        
        Args:
            message: The user's message
            chat_history: The chat history
            
        Returns:
            A dictionary of parameters for the products tool
        """
        # Build a prompt to extract parameters
        extract_prompt = dedent(f"""
        You are tasked with extracting parameters from a user's message to search for shoes in our database.
        
        Chat history:
        {chat_history.history_as_text()}
        
        User message: "{message}"
        
        Based on the user's message, extract the appropriate parameters for our product search tool:
        
        1. What action is the user trying to perform? Choose from:
           - search: The user wants to find products
           - details: The user wants details about a specific product
           - availability: The user wants to check if a product is available
           - category: The user wants to browse products in a category
        
        2. Based on the action, extract these parameters:
           - For 'search': Extract the query (what they're searching for)
           - For 'details': Extract the product_id (if mentioned)
           - For 'availability': Extract product_id, size, and color
           - For 'category': Extract the category_name
        
        Return your answer as a valid JSON object with the action and relevant parameters.
        For example: {{"action": "search", "query": "red nike running shoes"}}
        """)
        
        try:
            # Get the LLM's response
            response = await self.llm.ainvoke(extract_prompt)
            
            # Extract the JSON from the response
            json_text = response.content
            # If the response contains backticks (code blocks), extract just the JSON
            if "```" in json_text:
                json_text = json_text.split("```")[1]
                if json_text.startswith("json"):
                    json_text = json_text[4:]
            
            # Parse the JSON
            params = json.loads(json_text.strip())
            logger.info(f"Extracted parameters: {params}")
            return params
        except Exception as e:
            logger.error(f"Error extracting parameters: {str(e)}\n{traceback.format_exc()}")
            # Default to search with the full message as query
            return {"action": "search", "query": message}

    async def _generate_response_with_tool_result(self, params: dict, result: dict, message: str, chat_history: ChatHistory) -> str:
        """
        Generate a response using the result from the products tool.
        
        Args:
            params: The parameters used for the tool
            result: The result from the tool
            message: The user's message
            chat_history: The chat history
            
        Returns:
            A formatted response string
        """
        # If the tool returned a formatted response, use it
        if "response" in result and result["response"]:
            return result["response"]
        
        # Otherwise, build a prompt for the LLM to generate a response
        result_json = json.dumps(result, indent=2)
        response_prompt = dedent(f"""
        You are a helpful shopping assistant for a shoe store. You have access to our product database.
        
        Chat history:
        {chat_history.history_as_text()}
        
        User message: "{message}"
        
        I've queried our product database with these parameters:
        {json.dumps(params, indent=2)}
        
        Here's the result:
        {result_json}
        
        Please provide a helpful, conversational response to the user based on this information.
        If the query returned an error, apologize and suggest alternatives.
        If the query returned results, summarize them in a friendly way.
        """)
        
        try:
            # Get the LLM's response
            response = await self.llm.ainvoke(response_prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I'm sorry, I encountered an error while processing your request. Our product database is available, but I'm having trouble generating a response. Please try a simpler query."

    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """
        Process a user message and return a response using the products database.
        
        Args:
            message: The user's message
            chat_history: The chat history
            
        Returns:
            A response message
        """
        chat_history = chat_history or ChatHistory(messages=[])
        
        if not self.products_tool:
            # Fall back to basic LLM response if the products tool is not available
            response = await self.llm.ainvoke(dedent(f"""
                You are a helpful customer support bot for our shoe store.
                You need to provide information about our products, but you don't have access
                to our product database right now. Apologize for this limitation and offer
                to help with general questions about shoes.
                ---
                Chat history:
                {chat_history.history_as_text()}
                ---
                User message: {message.message}
                ---
                """))
                
            return ChatMessage(
                message=response.content,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=["Tell me about running shoes", "What brands do you carry?", "Do you have kids shoes?"],
                created_at=utcnow()
            )
        
        try:
            # Extract parameters from the message
            params = await self._extract_tool_parameters(message.message, chat_history)
            
            # Execute the appropriate action with the products tool
            result = await self._execute_tool_action(**params)
            
            # Generate a response using the result
            response_text = await self._generate_response_with_tool_result(
                params, result, message.message, chat_history
            )
            
            # Generate suggestions based on the action and result
            suggestions = self._generate_suggestions(params["action"], result)
            
            return ChatMessage(
                message=response_text,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=suggestions,
                created_at=utcnow()
            )
        except Exception as e:
            logger.error(f"Error in products agent: {str(e)}\n{traceback.format_exc()}")
            
            # Fall back to a simple response
            response = await self.llm.ainvoke(dedent(f"""
                You are a helpful customer support bot for our shoe store.
                You need to provide information about our products.
                An error occurred while trying to access the product database.
                Apologize for this error and offer general assistance.
                ---
                User message: {message.message}
                ---
                """))
                
            return ChatMessage(
                message=response.content,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=["Tell me about running shoes", "What brands do you carry?", "Do you have kids shoes?"],
                created_at=utcnow()
            )
    
    def _generate_suggestions(self, action: str, result: dict) -> List[str]:
        """
        Generate suggestions for the next user message based on the action and result.
        
        Args:
            action: The action that was executed
            result: The result of the action
            
        Returns:
            A list of suggestions
        """
        if action == "search":
            if "results" in result and result["results"]:
                # Suggest looking at details of one of the products
                product = result["results"][0]
                return [
                    f"Tell me more about the {product.get('name', 'first product')}",
                    "Show me more products",
                    "Do you have any running shoes?"
                ]
            else:
                # No results, suggest broader searches
                return [
                    "Show me all Nike shoes",
                    "What running shoes do you have?",
                    "Show me popular shoes"
                ]
        
        elif action == "details":
            if "details" in result and result["details"]:
                product = result["details"]
                return [
                    f"Is this available in size 10?",
                    f"Do you have this in red?",
                    "Show me similar products"
                ]
            else:
                return [
                    "Show me popular shoes",
                    "What's on sale?",
                    "Tell me about your running shoes"
                ]
        
        elif action == "availability":
            return [
                "Show me other colors",
                "Show me other sizes",
                "Do you have similar shoes?"
            ]
        
        elif action == "category":
            return [
                "Tell me about running shoes",
                "Show me basketball shoes",
                "What's on sale?"
            ]
        
        # Default suggestions
        return [
            "Show me popular shoes",
            "What's on sale?",
            "Do you have Nike shoes?"
        ]