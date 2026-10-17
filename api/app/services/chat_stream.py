import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.guardrails import RAGGuardrails
from app.domain.models import Message
from app.infrastructure.checkpoint import get_checkpointer
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.llm.factory import get_chat_model
from app.infrastructure.llm.interfaces import BaseChatModel, ChatMessage
from app.services.graph import (
    SYSTEM_PROMPT,
    CodebaseQAState,
    retrieve_context_node,
    validate_evidence_node,
)
from app.services.retrieval import SemanticRetrievalService

logger = logging.getLogger(__name__)


def sse_pack(event: str, data: Any) -> str:
    """Format payload according to standard Server-Sent Events (SSE) format."""
    payload = json.dumps(data) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {payload}\n\n"


class ChatStreamingService:
    """Orchestrates streaming QA generation, citation emission, and DB persistence."""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        retrieval_service: SemanticRetrievalService | None = None,
    ) -> None:
        self.llm = llm
        self.retrieval_service = retrieval_service

    async def stream_chat_response(
        self,
        conversation_id: str,
        repository_id: str,
        commit_sha: str | None,
        question: str,
        history: list[dict[str, str]],
        user_message_id: str,
        use_in_memory: bool = False,
    ) -> AsyncIterator[str]:
        """Stream response chunks via SSE and persist assistant message."""
        # 1. Emit start event
        yield sse_pack(
            "start",
            {
                "conversation_id": conversation_id,
                "user_message_id": user_message_id,
                "commit_sha": commit_sha,
            },
        )

        # 2. Execute retrieval node
        qa_state: CodebaseQAState = {
            "question": question,
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "history": history,
            "retrieved_chunks": [],
            "context_str": "",
            "has_sufficient_evidence": False,
            "citations": [],
            "answer": "",
        }

        retrieval_result = await retrieve_context_node(
            qa_state, retrieval_service=self.retrieval_service
        )
        qa_state.update(retrieval_result)

        # 3. Validate retrieved evidence
        validation_result = validate_evidence_node(qa_state)
        qa_state.update(validation_result)

        citations = qa_state.get("citations", [])
        # Emit citations early so UI can display references immediately
        yield sse_pack("citations", citations)

        accumulated_text = ""
        chat_model = self.llm or get_chat_model()

        try:
            if not qa_state.get("has_sufficient_evidence", False):
                # Insufficient evidence: stream explicit grounded message
                answer = qa_state["answer"]
                accumulated_text = answer
                yield sse_pack("chunk", answer)
            else:
                # Build messages for LLM streaming
                messages: list[ChatMessage] = [
                    ChatMessage(role="system", content=SYSTEM_PROMPT)
                ]
                for turn in history[-6:]:
                    r = turn.get("role", "user")
                    if r in ("user", "assistant"):
                        messages.append(
                            ChatMessage(role=r, content=turn.get("content", ""))
                        )

                prompt_content = (
                    f"Retrieved Codebase Context:\n\n{qa_state['context_str']}\n\n"
                    f"User Question: {question}\n\n"
                    "Provide a clear, accurate explanation grounded in the code above."
                )
                messages.append(ChatMessage(role="user", content=prompt_content))

                async for chunk in chat_model.astream(
                    messages=messages, temperature=0.1
                ):
                    accumulated_text += chunk
                    yield sse_pack("chunk", chunk)

            # Redact any accidental credential leakage before database commit
            accumulated_text = RAGGuardrails.inspect_for_secret_leakage(
                accumulated_text
            )

            # Persist assistant message in PostgreSQL
            async with async_session_factory() as session:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=accumulated_text,
                    status="completed",
                    citations=citations,
                )
                session.add(assistant_msg)
                await session.commit()
                await session.refresh(assistant_msg)
                assistant_msg_id = str(assistant_msg.id)

            # Save LangGraph checkpoint
            checkpointer = await get_checkpointer(use_in_memory=use_in_memory)
            config = {
                "configurable": {
                    "thread_id": conversation_id,
                    "checkpoint_ns": "",
                }
            }
            qa_state["answer"] = accumulated_text
            await checkpointer.aput(
                config=config,
                checkpoint={
                    "v": 1,
                    "id": f"chk-{assistant_msg_id}",
                    "ts": "",
                    "channel_values": {"qa_state": qa_state},
                    "channel_versions": {"qa_state": 1},
                    "versions_seen": {},
                },
                metadata={"step": "completed", "citations_count": len(citations)},
                new_versions={"qa_state": 1},
            )

            # Emit final completed event
            yield sse_pack(
                "done",
                {
                    "message_id": assistant_msg_id,
                    "conversation_id": conversation_id,
                    "status": "completed",
                },
            )

        except Exception as exc:
            logger.exception("Error during chat streaming: %s", exc)
            # Persist failed assistant message record if needed
            try:
                async with async_session_factory() as session:
                    failed_content = (
                        accumulated_text or "Error: Generation failed mid-stream."
                    )
                    failed_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=failed_content,
                        status="failed",
                        citations=citations if citations else None,
                    )
                    session.add(failed_msg)
                    await session.commit()
            except Exception as db_exc:
                logger.error("Failed to persist failed message status: %s", db_exc)

            yield sse_pack("error", {"error": str(exc), "partial": accumulated_text})
