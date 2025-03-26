from tkinter import END
from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from typing import List, Dict, Any
from llm_factory import LLMFactory
from utils import naive_utcnow
import logging
from config import LLM_MODEL, LLM_VENDOR
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """
    Knowledge agent that implements corrective RAG to provide accurate and verified information.
    """
    def __init__(self):
        super().__init__()

    def initialize(self) -> None:
        """Initialize the knowledge agent with required components"""
        # Initialize LLM / Agent / Vector store
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)
        
    async def process_message(self, message: ChatMessage, chat_history: ChatHistory = None) -> ChatMessage:
        
        """
        Process the message using corrective RAG and return the response asynchronously.
        """
        chat_history = chat_history or ChatHistory(messages=[])
        
        file_path = "RAG Dataset/FAQ.pdf"
        loader = PyPDFLoader(file_path)
        pages = []
        async for page in loader.alazy_load():
            pages.append(page)
        vector_store = InMemoryVectorStore.from_documents(pages, OpenAIEmbeddings())
        # Create a retriever object on the vector store
        retriever = vector_store.as_retriever()
        
        docs = retriever.get_relevant_documents(message.message)
        # Define retrieval function
        def retrieve(state):
            """Retrieve documents based on query."""
            query = state["query"]
            docs = retriever.get_relevant_documents(query)
            return {"query": query, "documents": docs}

        # Define LLM generation function
        def generate(state):
            """Generate response using LLM and retrieved documents."""
            query = state["query"]
            docs = state["documents"]
            
            # Combine retrieved context
            context = "\n\n".join([doc.page_content for doc in docs])
            prompt = f"Answer the following query using the retrieved information:\nQuery: {query}\nContext: {context}\nResponse:"

            response = self.llm.invoke(prompt)
            return {"query": query, "documents": docs, "response": response}

        # === 3. Build LangGraph ===
        graph = StateGraph()

        # Add nodes
        graph.add_node("retrieve", retrieve)
        graph.add_node("generate", generate)

        # Define execution flow
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)

        # Compile chain
        rag_chain = graph.compile()

        # === 4. Run Query ===
        query = "What is the refund policy?"
        output = rag_chain.invoke({"query": query})


        try:

            # do some work.. return a chat message
            
            return ChatMessage(
                message=output,
                sender="ai",
                suggestions=[],
                created_at=naive_utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in knowledge agent processing: {e}", exc_info=True)
            return ChatMessage(
                message="I apologize, but I encountered an error while processing your request. Please try again or contact support if the issue persists.",
                sender="ai",
            )
    