import pytest
from app.agent.llm_adapter import LLMAdapter


def test_llm_adapter_mock_provider():
    model = LLMAdapter.get_chat_model(provider="mock")
    assert model is not None


def test_llm_adapter_unsupported_provider():
    with pytest.raises(ValueError) as exc_info:
        LLMAdapter.get_chat_model(provider="unsupported_provider_xyz")
    assert "Unsupported LLM provider" in str(exc_info.value)


def test_llm_adapter_groq_missing_key():
    with pytest.raises(ValueError) as exc_info:
        LLMAdapter.get_chat_model(provider="groq", api_key="")
    assert "GROQ_API_KEY is not configured" in str(exc_info.value)
