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
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    question: str
    documents: list[str]
    generated_answer: str

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
        
        user_prompt = message.message
        
        """
        Process the message using corrective RAG and return the response asynchronously.
        """
        # chat_history = chat_history or ChatHistory(messages=[])
        
        file_path = "RAG Dataset/FAQ.pdf"
        loader = PyPDFLoader(file_path)
        pages = []
        async for page in loader.alazy_load():
            pages.append(page)
        vector_store = InMemoryVectorStore.from_documents(pages, OpenAIEmbeddings())
        # Create a retriever object on the vector store
        retriever = vector_store.as_retriever()
        
        #docs = retriever.invoke(question)
        # Define retrieval function
        def retrieve_documents(state: GraphState):
            """Retrieve documents based on query."""
            query = state["question"]
            docs = retriever.invoke(query)
            return {"question": query, "documents": docs}

        # Define LLM generation function
        def generate_answer(state: GraphState):
            """Generate response using LLM and retrieved documents."""
            
            query = state["question"]
            docs = state["documents"]
            
            prompt = PromptTemplate.from_template(
                    "Answer the question based on the context provided. \n"
                    "Question: {question}\n"
                    "Context: {context}\n"
                    "Answer: "
            )

            # Combine retrieved context
            context = "\n".join([doc.page_content for doc in docs])
            logger.info(f"Logging context: '{context}...'")
            prompt = prompt.format(question=query, context=context)
            response = self.llm.invoke(prompt).content
            return {"question": query, "documents": docs, "response": response}

        # === 3. Build LangGraph ===
        graph_builder = StateGraph(GraphState)

        # Add nodes
        graph_builder.add_node("retrieve", retrieve_documents)
        graph_builder.add_node("generate", generate_answer)

        # Define execution flow
        graph_builder.add_edge(START,"retrieve")
        graph_builder.add_edge("retrieve","generate")
        graph_builder.add_edge("generate", END)

        # Compile chain
        graph = graph_builder.compile()

        # === 4. Run Query ===
        if not user_prompt.strip():  
            user_prompt = "What is the refund policy?"
        logger.info(f"Before invoking LLM: Query Message: '{user_prompt}...'")
        output = graph.invoke({"question": user_prompt})
        
        #doc_summary = output.get("documents", {})

        # Extract page_content from each Document object
        page_contents = [doc.page_content for doc in output['documents']]
        doc_response = ""
        for content in page_contents:
            doc_response += f" {content} \n"
        doc_response += " \n"

        response_message = doc_response
        logger.info(f"After invoking LLM - Message: '{response_message}...'")
        

        try:

            # do some work.. return a chat message
            
            return ChatMessage(
                message=response_message,
                conversation_id=message.conversation_id,
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
    
