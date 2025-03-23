from langchain.chat_models.base import BaseChatModel
from langchain.chat_models.openai import ChatOpenAI
from langchain.chat_models.anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from typing import Literal

class LLMFactory:
    """
    Factory class for creating LLM instances.
    """
    @staticmethod
    def create_llm(model_name: str, vendor: Literal["openai", "anthropic", "azure"]) -> BaseChatModel:
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