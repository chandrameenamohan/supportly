from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from textwrap import dedent
from utils import utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR

class ProductsAgent(BaseAgent):
    """
    The products agent is responsible for providing information about the products.
    """

    def __init__(self):
        super().__init__()
        self.llm = None

    def initialize(self):
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)

    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        # TODO: Implement this agent with necessary logic and retrieval tooling.
        response = await self.llm.ainvoke(dedent("""
            You are a helpful customer support bot for Acme Show, Inc. An online retailer of shoes of all types.
            You are given a message from a user.
            You need to provide information about the products.
            ---
            User message: {message.message}
            ---
            """))

        return ChatMessage(
            message=response.content,
            conversation_id=message.conversation_id,
            sender="ai",
            suggestions=[],
            created_at=utcnow()
        )