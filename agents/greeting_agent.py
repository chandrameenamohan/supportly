from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from textwrap import dedent
from utils import naive_utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR

class GreetingAgent(BaseAgent):
    """
    The greeting agent is responsible for greeting the user and asking them how they are doing.
    """

    def __init__(self):
        super().__init__()
        self.llm = None

    def initialize(self):
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)
    
    def _greeting_prompt(self, message: str, chat_history: ChatHistory) -> str:
        prompt = dedent("""**You are a helpful customer support bot for Acme Shoe Store, Inc. An online retailer of shoes of all types.**
                        ---
                        **Instructions:**
                        Greet the user with a friendly message.
                        """)

        if chat_history:
            prompt += f"\n---\nChat history: {chat_history.history_as_text()}"

        if message:
            prompt += f"\n---\nThe user said: {message}"

        return prompt


    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        greeting_prompt = self._greeting_prompt(message.message, chat_history)
        response = await self.llm.ainvoke(greeting_prompt)

        return ChatMessage(
            message=response.content,
            conversation_id=message.conversation_id,
            sender="ai",
            suggestions=None,
            created_at=naive_utcnow()
        )