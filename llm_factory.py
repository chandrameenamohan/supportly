from langchain.chat_models.base import BaseChatModel
from langchain.chat_models.openai import ChatOpenAI
from langchain.chat_models.anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from typing import Literal, List, Dict, Any, Optional, Union
import os
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.embeddings import Embeddings
from config import EMBEDDING_MODEL, LLM_MODEL, LLM_VENDOR, EMBEDDING_VENDOR

class DummyLLM(BaseChatModel):
    """A dummy LLM that returns hardcoded responses for testing."""
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager = None, **kwargs) -> ChatResult:
        """Generate a dummy response."""
        dummy_message = AIMessage(content="This is a dummy response for testing. The real app requires valid API keys.")
        return ChatResult(generations=[ChatGeneration(message=dummy_message, generation_info={})])
    
    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager = None, **kwargs) -> ChatResult:
        """Generate a dummy response asynchronously."""
        dummy_message = AIMessage(content="This is a dummy response for testing. The real app requires valid API keys.")
        return ChatResult(generations=[ChatGeneration(message=dummy_message, generation_info={})])
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "dummy"
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {"model_name": "dummy"}


class DummyEmbeddings(Embeddings):
    """A dummy embeddings model that returns hardcoded responses for testing."""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents."""
        return [[0.0] * 1536 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query."""
        return [0.0] * 1536
        

class LLMFactory:
    """
    Factory class for creating LLM instances.
    """
    @staticmethod
    def create_llm(model_name: str, vendor: Literal["openai", "anthropic", "azure", "dummy"]) -> BaseChatModel:
        # Use dummy mode if explicitly specified or if no valid API keys are found
        if vendor == "dummy":
            print("Using dummy LLM for testing")
            return DummyLLM()
        
        # Check for missing or dummy API keys and fall back to dummy mode
        if vendor == "openai" and (os.getenv("OPENAI_API_KEY") is None or os.getenv("OPENAI_API_KEY").startswith("sk-dummy")):
            print("WARNING: Using dummy LLM because no valid OpenAI API key was found")
            return DummyLLM()
            
        if vendor == "openai":
            return ChatOpenAI(
                model=model_name,
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        elif vendor == "anthropic":
            return ChatAnthropic(
                model="claude-3-5-sonnet-20240620",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        elif vendor == "azure":
            return AzureChatOpenAI(
                model=model_name,
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")
    
    def create_embeddings(model_name: str = EMBEDDING_MODEL, vendor: Literal["openai", "azure", "dummy"] = EMBEDDING_VENDOR) -> Embeddings:
        if vendor == "openai":
            return OpenAIEmbeddings(model=model_name)
        elif vendor == "azure" \
            and os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT") \
                and os.getenv("AZURE_OPENAI_API_KEY"):
            return AzureOpenAIEmbeddings(model=model_name, 
                                         azure_endpoint=os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT"), 
                                         openai_api_version=os.getenv("AZURE_OPENAI_EMBEDDING_VERSION"))
        elif vendor == "dummy":
            return DummyEmbeddings()
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")