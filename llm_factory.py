from langchain.chat_models.base import BaseChatModel
from langchain.chat_models.openai import ChatOpenAI
from langchain.chat_models.anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from typing import Literal, List, Dict, Any, Optional, Union
import os
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

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