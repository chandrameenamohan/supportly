import logging
from typing import List
from utils import naive_utcnow
from message_logger import get_message_logger
from llm_factory import LLMFactory
from .base_agent import BaseAgent
from textwrap import dedent
from chat_models import ChatHistory, ChatMessage 
from config import LLM_MODEL, LLM_VENDOR, DB_URL
from .knowledge_agent import KnowledgeAgent
from .greeting_agent import GreetingAgent
from .orders_agent import OrdersAgent
from .products_agent import ProductsAgent
from .reports_agent import ReportsAgent

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    The orchestrator agent is responsible for determining which workflow
    to use for a given user query.
    """
    version: str = "0.1"
    agent_name: str = "orchestrator"

    def __init__(self):
        super().__init__()
        self.agent = None
        self.llm = None
        self.knowledge_agent = None
        self.greeting_agent = None
        self.orders_agent = None
        self.products_agent = None
        self.reports_agent = None
        self.downstream_agents = {}

    def initialize(self) -> None:
        """Initialize the orchestrator agent with required components"""
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)
        
        # Initialize specialized agents
        self.knowledge_agent = KnowledgeAgent()
        self.knowledge_agent.initialize()
        self.greeting_agent = GreetingAgent()
        self.greeting_agent.initialize()
        self.orders_agent = OrdersAgent()
        self.orders_agent.initialize()
        self.products_agent = ProductsAgent()
        self.products_agent.initialize()
        self.reports_agent = ReportsAgent()
        self.reports_agent.initialize()

        self.downstream_agents = {
            'initial_greeting': self.greeting_agent,
            'knowledge': self.knowledge_agent,
            'greeting': self.greeting_agent,
            'orders': self.orders_agent,
            'products': self.products_agent,
            'reports': self.reports_agent,
            'other': self.knowledge_agent
        }

    async def _generate_response_suggestions(self, ai_response: str, chat_history: ChatHistory) -> List[str]:
        """
        This is a placeholder for now.
        TODO: return a list of suggestions for the user's next message.
        """
        return ["Order status", "Product information", "Support request"]
    
    async def _classify_intent(self, message: str, chat_history: ChatHistory) -> str:
        """Classify the user's intent to determine which agent should handle it"""

        # Handle empty messages or new conversations
        if not chat_history.messages and not message:
            return 'greeting'

        # Define valid intents and their descriptions
        # TODO: fine tune the agent descriptions to improve intent classification
        intent_descriptions = {
            'greeting': "If the user is greeting the bot, introducing themselves, or making small talk",
            'orders': "If the user is asking about their order",
            'products': "If the user is asking about the products",
            'reports': "If the user is asking for reports, analytics, inventory data, or business insights",
            'other': "If the user's intent is not clear from the message, or if the user is asking a question that doesn't fall into the other categories"
        }
        
        # Check for reports-related keywords
        reports_keywords = ["report", "inventory", "analytics", "analysis", "statistics", "sales data", "price analysis"]
        message_lower = message.lower()
        for keyword in reports_keywords:
            if keyword in message_lower:
                logger.info(f"REPORTS KEYWORD DETECTED: '{keyword}' - Message: '{message[:50]}...'")
                return 'reports'
        
        # Build the prompt with intent descriptions
        intent_options = "\n".join([f"- '{intent}': {desc}" for intent, desc in intent_descriptions.items()])
        intent_prompt = dedent(f"""Classify the user's intent from the user message:
            ---
            Return exactly one of the following intents:
            {intent_options}
            ---
            Chat history:
            {chat_history.history_as_text()}
            ---
            User message: "{message}"
            """)
        
        response = await self.llm.ainvoke(intent_prompt)
        raw_intent = response.content.lower().strip()
        
        # Match to valid intents or default to knowledge
        for intent in intent_descriptions.keys():
            if intent in raw_intent:
                logger.info(f"INTENT DETECTED: {intent.upper()} - Message: '{message[:50]}...'")
                
                # Log payment-related queries
                if 'payment' in message.lower() or 'billing' in message.lower():
                    logger.info(f"PAYMENT-RELATED QUERY DETECTED - Routing to: {intent.upper()}")
                
                return intent
                
        # Default to knowledge intent
        logger.info(f"INTENT DETECTED: KNOWLEDGE - Message: '{message[:50]}...'")
        return 'other'

    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """
        Process the message and return the response by routing to the appropriate agent.
        """
        chat_history = chat_history or ChatHistory(messages=[])

        # Client sends an empty message to start a new conversation, this should 
        # always be routed to the greeting agent without any intent evaluation.
        if not chat_history.messages and message.message == "":
            intent = "initial_greeting"
        else:
            intent = await self._classify_intent(message.message, chat_history)
        
        # Get appropriate agent based on intent
        target_agent = self.downstream_agents.get(intent, self.knowledge_agent)  # Default to knowledge agent
        
        logger.info(f"🔄 ROUTING TO: {target_agent.agent_name.upper()} AGENT")
        response = await target_agent.process_message(message, chat_history)

        # Process response and generate suggestions, if downstream agent returns suggestions, use those.
        if response.suggestions:
            suggestions = response.suggestions
        else:
            suggestions = await self._generate_response_suggestions(response.message, chat_history)

        # Log the response
        message_logger = get_message_logger(DB_URL)
        response_id = await message_logger.log_message(
            conversation_id=message.conversation_id,
            sender="ai",
            message_text=response.message,
        )

        logger.info(response) 
        response.message_id = response_id
        response.created_at = response.created_at or naive_utcnow()
        response.suggestions = suggestions
        response.sender = "ai"
        response.conversation_id = response.conversation_id or message.conversation_id
        response.intent = intent

        return response

