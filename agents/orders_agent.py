from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from textwrap import dedent
from utils import naive_utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR

class OrdersAgent(BaseAgent):
    """
    The greeting agent is responsible for greeting the user and asking them how they are doing.
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
            You need to determine if the user is asking about their order.
            If they are, you need to provide them with the information they need.
            ---
            User message: {message.message}
            ---
            """))

        return ChatMessage(
            message=response.content,
            conversation_id=message.conversation_id,
            sender="ai",
            chat_history=chat_history,
            suggestions=[],
            created_at=naive_utcnow()
        )