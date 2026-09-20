import os
from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.core.config import settings


class LLMConfig(BaseModel):
    provider: str
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = 2048
    timeout_seconds: float = 30.0


class LLMAdapter:
    """
    Factory & Abstraction layer for LLM providers.
    Allows zero-code switching between Groq, Ollama, OpenAI-compatible, and Mock providers.
    """

    @staticmethod
    def get_chat_model(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        api_key: Optional[str] = None,
    ) -> BaseChatModel:
        selected_provider = (provider or settings.LLM_PROVIDER).lower()

        if selected_provider == "groq":
            key = api_key if api_key is not None else settings.GROQ_API_KEY
            if not key or key == "your_groq_api_key_here":
                raise ValueError(
                    "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in backend/.env"
                )
            model = model_name or settings.GROQ_MODEL or "openai/gpt-oss-120b"
            return ChatGroq(
                groq_api_key=key,
                model_name=model,
                temperature=temperature,
                max_retries=2,
                timeout=30.0,
            )

        elif selected_provider == "ollama":
            from langchain_community.chat_models import ChatOllama
            ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = model_name or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            return ChatOllama(
                base_url=ollama_base,
                model=model,
                temperature=temperature,
            )

        elif selected_provider == "mock":
            # For unit testing without network
            from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
            return FakeMessagesListChatModel(responses=[])

        else:
            raise ValueError(
                f"Unsupported LLM provider: '{selected_provider}'. Supported: 'groq', 'ollama', 'mock'."
            )
