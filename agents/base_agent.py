from abc import ABC, abstractmethod
from chat_models import ChatMessage, ChatHistory


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """
    version: str = "0.0.1" # This should be overridden by subclasses.
    agent_name: str = "base"# This should be overridden by subclasses.

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the agent with the given tools.

        This method is called after initialization to setup necessary components, 
        like language models, memory, tools, etc. 
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """
        Process the message and return the response.

        This is the core method that each agent must implement.
        """
        raise NotImplementedError("Subclasses must implement this method")
