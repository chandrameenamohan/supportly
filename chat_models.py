from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from utils import naive_utcnow


class ChatHistoryItem(BaseModel):
    """Chat history item for an agent."""
    role: Literal["user", "human", "assistant", "ai"]
    content: str
    created_at: Optional[datetime] = None

    def is_user_message(self) -> bool:
        """Check if the message is a user message."""
        return self.role.lower() in ["user", "human"]

    def is_assistant_message(self) -> bool:
        """Check if the message is an assistant message."""
        return self.role.lower() in ["assistant", "ai"]


class ChatHistory(BaseModel):
    """Chat history for an agent."""
    messages: List[ChatHistoryItem]

    def add_message(self, message: ChatHistoryItem) -> None:
        """Add a message to the chat history."""
        self.messages.append(message)

    def get_last_message(self) -> ChatHistoryItem:
        """Get the last message from the chat history."""
        return self.messages[-1]
    
    def history_list(self) -> List[Tuple[str, str]]:
        """Get the chat history as a list of tuples."""
        return [(m.role, m.content) for m in self.messages]

    def history_as_text(self) -> str:
        """Get the chat history as a string for use in a prompt."""
        messages = self.history_list()
        return ChatPromptTemplate.from_messages(messages).format()


class ChatHistoryFactory:
    """Factory class for creating ChatHistory objects."""

    @staticmethod
    def from_db(history: List[Dict[str, Any]]) -> ChatHistory:
        """Create a ChatHistory object from a list of dictionaries."""
        return ChatHistory(messages=[
            ChatHistoryItem(
                role=m["sender"],
                content=m["message_text"],
                created_at=m["created_at"]
            ) for m in history
        ])


class MessagePayload(BaseModel):
    """A model representing the payload of a chat message."""
    message: str
    conversation_id: Optional[str] = None


class ChatMessage(BaseModel):
    """A model representing the body of a chat message."""
    message: str
    message_id: Optional[str] = None
    sender: Literal["user", "ai"]
    conversation_id: Optional[str] = None
    chat_history: Optional[ChatHistory] = None
    created_at: Optional[datetime] = None
    suggestions: Optional[List[str]] = None
    intent: Optional[str] = None

    @staticmethod
    def from_chat_payload(message_payload: MessagePayload) -> 'ChatMessage':
        """Create a Message object from a chat message payload."""
        return ChatMessage(
            message=message_payload.message,
            conversation_id=message_payload.conversation_id,
            sender="user",
            created_at=naive_utcnow()
        )


