from typing import Optional, List, Dict
import logging
from datetime import timedelta
from fastapi import FastAPI, HTTPException
from agents import OrchestratorAgent
from message_logger import get_message_logger
from chat_models import ChatMessage, ChatHistoryFactory, MessagePayload
from fastapi.middleware.cors import CORSMiddleware
from utils import naive_utcnow
from dotenv import load_dotenv

load_dotenv()
from config import DB_URL

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()


# Define CORS middleware to allow all origins (or specify a list of allowed origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; replace with ["http://localhost:3000"] for more security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Global orchestrator agent to avoid re-initialization costs
_orchestrator = None

def get_orchestrator():
    """Singleton pattern to get or create orchestrator agent"""
    global _orchestrator
    if not _orchestrator:
        logger.info("Initializing orchestrator agent")
        _orchestrator = OrchestratorAgent()
        _orchestrator.initialize()
    return _orchestrator

@app.post("/chat")
async def message(message_payload: MessagePayload):
    try:
        logger.info(f"Received message: {message_payload.message[:50]}...")
        message_body = ChatMessage.from_chat_payload(message_payload)
        
        # Get the message logger
        message_logger = get_message_logger(DB_URL)

        chat_history = None
        
        async def get_or_create_conversation():
            if not message_body.conversation_id:
                return await message_logger.start_conversation(
                    user_id="anonymous",
                )

            history = await message_logger.get_conversation_history(message_body.conversation_id)
            if not history:
                return message_body.conversation_id

            last_message = history[-1]
            conversation_expired = last_message["created_at"] < naive_utcnow() - timedelta(hours=2)
            
            if conversation_expired:
                return await message_logger.start_conversation(
                    user_id="anonymous",
                )
            
            nonlocal chat_history
            chat_history = ChatHistoryFactory.from_db(history)
            return message_body.conversation_id

        message_body.conversation_id = await get_or_create_conversation()
        message_body.chat_history = chat_history

        # Log the user's message
        message_body.message_id = await message_logger.log_message(
            conversation_id=message_body.conversation_id,
            sender="user",
            message_text=message_body.message,
        )

        # Get the orchestrator agent
        orchestrator = get_orchestrator()
        
        # Process the message with chat history if available
        response = await orchestrator.process_message(
            message=message_body,
            chat_history=chat_history
        )
        
        # Extract intent if available
        intent = response.intent
        logger.info(f"Processed message with intent: {intent} - Response: {response.message[:50]}...")
        
        # Return the response with conversation tracking info
        return response

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")



