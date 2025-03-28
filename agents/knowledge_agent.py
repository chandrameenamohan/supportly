from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from typing import List
from pathlib import Path
from llm_factory import LLMFactory
from utils import naive_utcnow
import logging
from config import LLM_MODEL, LLM_VENDOR
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import time
from pypdf import PdfReader
from chromadb import PersistentClient


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
        data_dir = Path("RAG Dataset")
        self.document_paths = list(data_dir.glob("*.pdf")) 
        self.embeddings = LLMFactory.create_embeddings()
        client = PersistentClient(path="./chroma_db")
        try:
            self.vector_store = client.get_collection("supportly")
        except Exception as e:
            self.vector_store = client.create_collection("supportly")

    def retrieval(self, query: str) -> List[str]:
        embedded_query = self.embeddings.embed_query(query)
        results = self.vector_store.query(query_embeddings=embedded_query, n_results=5)
        return results["documents"][0]

    def load_and_process_documents(self) -> list[str]:
        """Load and process OPM documents."""
        chunks = []
        for path in self.document_paths:
            print("New document:")
            with open(path, "rb") as f:
                pdf_reader = PdfReader(f)
                for page in pdf_reader.pages:
                    print("New page:")
                    text = page.extract_text()
                    if len(text) < 100:  # Skip very short pages
                        continue
                        
                    # Split into sentences and group them into chunks of ~1000 characters
                    current_chunk = ""
                    for sentence in text.split(". "):
                        if len(current_chunk) + len(sentence) > 1000:
                            if current_chunk:  # Only add non-empty chunks
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += ". " + sentence if current_chunk else sentence
                    
                    if current_chunk:  # Add the last chunk
                        chunks.append(current_chunk.strip())
        
        # Create embeddings and store in vector database in batches of 50
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            print(f"Processing batch {i // batch_size + 1} of {len(chunks) // batch_size}")
            batch_chunks = chunks[i:i + batch_size]
            batch_vectors = self.embeddings.embed_documents(batch_chunks)
            batch_ids = [f"id{j}" for j in range(i, i + len(batch_chunks))]
            self.vector_store.add(documents=batch_chunks, embeddings=batch_vectors, ids=batch_ids)
            time.sleep(10)
        
    async def process_message(self, message: ChatMessage, chat_history: ChatHistory = None) -> ChatMessage:
        
        user_prompt = message.message
        logger.info(f"Knowledge Agent - Logging User Prompt: '{user_prompt}...'")
        """
        Process the message using corrective RAG and return the response asynchronously.
        """
        
        # Define retrieval function
        def retrieve_documents(state: GraphState):
            """Retrieve documents based on query."""
            query = state["question"]
            docs = self.retrieval(query)
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
            context = "\n\n".join(docs)
            logger.info(f"Knowledge Agent - Logging context: '{context}...'")
            prompt = prompt.format(question=query, context=context)
            response = self.llm.invoke(prompt).content
            logger.info(f"Knowledge Agent - LLM responded as: '{response}...'")
            return {"question": query, "documents": docs, "generated_answer": response}

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
        logger.info(f"Knowledge Agent - Before invoking LLM: Query Message: '{user_prompt}...'")
        output = graph.invoke({"question": user_prompt})
        logger.info(f"Knowledge Agent - After graph invoke: Output Structure: '{output}...'")
        doc_response = ""
        doc_response = output.get("generated_answer", None)

        logger.info(f"Knowledge Agent - After invoking LLM - Message: '{doc_response}...'")
        try:
            return ChatMessage(
                message=doc_response,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=None,
                created_at=naive_utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in knowledge agent processing: {e}", exc_info=True)
            return ChatMessage(
                message="I apologize, but I encountered an error while processing your request. Please try again or contact support if the issue persists.",
                sender="ai",
            )