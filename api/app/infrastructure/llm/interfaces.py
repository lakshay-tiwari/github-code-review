from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Normalized chat message passed into LLM providers."""

    role: str = Field(
        description="Role of the sender: 'system', 'user', or 'assistant'"
    )
    content: str = Field(description="Textual content of the message")


class ChatResponse(BaseModel):
    """Normalized completion response returned by LLM providers."""

    content: str = Field(description="Generated textual content")
    model: str = Field(description="Model name that generated the response")
    usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token stats (prompt_tokens, completion_tokens, total_tokens)",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Reason generation terminated (e.g., 'stop', 'length')",
    )


class BaseChatModel(ABC):
    """Abstract interface hiding provider-specific LLM implementations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'groq')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the specific model (e.g. 'llama-3.3-70b-versatile')."""
        ...

    @abstractmethod
    async def agenerate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Asynchronously generate a complete chat completion."""
        ...

    @abstractmethod
    async def astream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Asynchronously stream chunks of completion text."""
        ...
