from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.infrastructure.llm.interfaces import BaseChatModel, ChatMessage, ChatResponse


class GroqChatProvider(BaseChatModel):
    """Groq chat completion provider wrapping LangChain's ChatGroq client."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                "GROQ_API_KEY must be provided to initialize GroqChatProvider"
            )

        self._model = model
        self._temperature = temperature
        self._client = ChatGroq(
            groq_api_key=api_key,
            model_name=model,
            temperature=temperature,
            max_retries=max_retries,
        )

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    def _convert_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert domain ChatMessage models to LangChain message types."""
        lc_messages: list[BaseMessage] = []
        for msg in messages:
            role = msg.role.lower()
            if role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            else:
                lc_messages.append(HumanMessage(content=msg.content))
        return lc_messages

    async def agenerate(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Asynchronously invoke Groq and return a normalized ChatResponse."""
        lc_messages = self._convert_messages(messages)
        call_kwargs: dict[str, Any] = {**kwargs}
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens

        response = await self._client.ainvoke(lc_messages, **call_kwargs)

        # Extract text content
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        # Extract token usage metadata safely
        usage: dict[str, int] = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                "total_tokens": response.usage_metadata.get("total_tokens", 0),
            }
        elif (
            hasattr(response, "response_metadata")
            and "token_usage" in response.response_metadata
        ):
            token_usage = response.response_metadata["token_usage"]
            usage = {
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0),
            }

        finish_reason = None
        if hasattr(response, "response_metadata"):
            finish_reason = response.response_metadata.get("finish_reason")

        return ChatResponse(
            content=content,
            model=self._model,
            usage=usage,
            finish_reason=finish_reason,
        )

    async def astream(
        self,
        messages: list[ChatMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Asynchronously stream chunks of text from Groq."""
        lc_messages = self._convert_messages(messages)
        call_kwargs: dict[str, Any] = {**kwargs}
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens

        async for chunk in self._client.astream(lc_messages, **call_kwargs):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content
            elif chunk.content:
                yield str(chunk.content)
