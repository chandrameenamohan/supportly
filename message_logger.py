import uuid
import logging
from typing import Optional, Dict, List
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from config import DB_URL
from utils import naive_utcnow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_message_logger = None

# Database configuration
Base = declarative_base()


# Define SQLAlchemy models
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = sa.Column(sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = sa.Column(sa.String, nullable=False) # This is just a placeholder for now.
    created_at = sa.Column(sa.DateTime, default=naive_utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, default=naive_utcnow, onupdate=naive_utcnow)


class Message(Base):
    __tablename__ = "messages"
    
    id = sa.Column(sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = sa.Column(sa.String(36), sa.ForeignKey("conversations.id"), nullable=False)
    created_at = sa.Column(sa.DateTime, default=naive_utcnow, index=True)
    updated_at = sa.Column(sa.DateTime, default=naive_utcnow, onupdate=naive_utcnow)
    sender = sa.Column(sa.String, nullable=False)  # "user" or "ai"
    message_text = sa.Column(sa.Text, nullable=False)


class UserSurvey(Base):
    __tablename__ = "user_survey"
    
    id = sa.Column(sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = sa.Column(sa.String(36), sa.ForeignKey("conversations.id"), nullable=False)
    satisfaction = sa.Column(sa.Integer, nullable=False)  # 1-5 scale
    feedback = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=naive_utcnow, index=True)

class MessageLogger:
    """Message logging system for chatbot conversations."""
    
    def __init__(self, db_url: str):
        """
        Initialize the message logger.
        
        Args:
            db_url: Database connection URL (e.g., "sqlite+aiosqlite:///database.db" or "postgresql+asyncpg://user:pass@localhost/dbname")
        """
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self._initialized = False
        
    async def initialize(self):
        """Initialize the database schema if it doesn't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._initialized = True
        logger.info("Message logger initialized")
        
    async def start_conversation(self, user_id: str = "demo") -> str:
        """
        Start a new conversation and return the conversation ID.
        
        Args:
            user_id: Identifier for the user
            
        Returns:
            str: The UUID of the created conversation
        """
        if not self._initialized:
            await self.initialize()
            
        conversation = Conversation(
            user_id=user_id,
        )
        
        try:
            async with self.async_session() as session:
                session.add(conversation)
                await session.commit()
                return str(conversation.id)
        except SQLAlchemyError as e:
            logger.error(f"Error starting conversation: {e}")
            # Return a UUID anyway so the application can continue
            return str(uuid.uuid4())
    
    async def log_message(
        self, 
        conversation_id: str, 
        sender: str, 
        message_text: str, 
    ) -> str:
        """
        Log a message and return the message ID.
        
        Args:
            conversation_id: UUID of the conversation
            sender: Who sent the message ("user" or "bot")
            message_text: Content of the message
            
        Returns:
            str: The UUID of the created message
        """
        if not self._initialized:
            await self.initialize()
            
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            message_text=message_text,
        )
        
        try:
            async with self.async_session() as session:
                session.add(message)
                await session.commit()
                return str(message.id)
        except SQLAlchemyError as e:
            logger.error(f"Error logging message: {e}")
            return str(uuid.uuid4())
    
    
    async def log_user_feedback(
        self,
        conversation_id: str,
        satisfaction: int,
        feedback: Optional[str] = None,
    ) -> str:
        """
        Log user feedback for a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            satisfaction: User satisfaction rating (1-5)
            feedback: Optional text feedback from the user
            
        Returns:
            str: The UUID of the created feedback entry
        """
        if not self._initialized:
            await self.initialize()
            
        if not 1 <= satisfaction <= 5:
            logger.warning(f"Invalid satisfaction rating: {satisfaction}. Must be between 1 and 5.")
            satisfaction = max(1, min(satisfaction, 5))
            
        user_survey = UserSurvey(
            conversation_id=conversation_id,
            satisfaction=satisfaction,
            feedback=feedback,
        )
        
        try:
            async with self.async_session() as session:
                session.add(user_survey)
                await session.commit()
                return str(user_survey.id)
        except SQLAlchemyError as e:
            logger.error(f"Error logging user feedback: {e}")
            return str(uuid.uuid4())
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Retrieve the full history of a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            
        Returns:
            List[Dict]: List of messages in the conversation with workflows
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            async with self.async_session() as session:
                query = (
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(desc(Message.created_at))
                    .limit(limit)
                )
                
                result = await session.execute(query)
                messages = result.scalars().all()
                logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")
                
                return [
                    {
                        "id": str(msg.id),
                        "sender": msg.sender,
                        "message_text": msg.message_text,
                        "created_at": msg.created_at,
                    }
                    for msg in messages
                ][::-1] # reverse the order of the messages to restore to chronological order
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
# Singleton pattern to get or create a message logger instance
def get_message_logger(url: str = DB_URL) -> MessageLogger:
    global _message_logger
    if _message_logger is None or _message_logger.db_url != url:
        _message_logger = MessageLogger(url)
    return _message_logger
