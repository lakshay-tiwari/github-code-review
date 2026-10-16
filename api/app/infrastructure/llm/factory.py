import logging

from app.core.config import settings
from app.infrastructure.llm.groq_provider import GroqChatProvider
from app.infrastructure.llm.interfaces import BaseChatModel

logger = logging.getLogger("cortex.llm.factory")

_chat_model_instances: dict[str, BaseChatModel] = {}


def get_chat_model(
    provider: str | None = None,
    force_new: bool = False,
) -> BaseChatModel:
    """Resolve and return an initialized BaseChatModel provider instance.

    Uses settings.LLM_PROVIDER ('groq') as default if not explicitly specified.
    Caches provider instances to avoid redundant initialization.
    """
    provider_name = (provider or settings.LLM_PROVIDER).lower().strip()

    if not force_new and provider_name in _chat_model_instances:
        return _chat_model_instances[provider_name]

    if provider_name == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured in the environment. "
                "Cannot initialize Groq chat provider."
            )
        instance = GroqChatProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
    else:
        raise ValueError(
            f"Unsupported LLM provider '{provider_name}'. "
            "Supported providers: ['groq']"
        )

    _chat_model_instances[provider_name] = instance
    return instance


def reset_chat_model_instances() -> None:
    """Clear cached chat model instances (primarily for test isolation)."""
    _chat_model_instances.clear()
