import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class UserMemoryService:
    """Bounded, privacy-preserving interface for user-level long-term memory.

    Isolates memory vectors into a dedicated Qdrant collection ('cortex_user_memory')
    and scopes every interaction strictly by authenticated Clerk user_id.
    """

    def __init__(self, enabled: bool | None = None) -> None:
        self.enabled = settings.MEM0_ENABLED if enabled is None else enabled
        self._memory_client: Any = None

    def _get_client(self) -> Any:
        if not self.enabled:
            return None

        if self._memory_client is None:
            try:
                from mem0 import Memory

                config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "host": settings.QDRANT_HOST,
                            "port": settings.QDRANT_HTTP_PORT,
                            "collection_name": settings.MEM0_COLLECTION_NAME,
                        },
                    },
                    "version": "v1.1",
                }
                self._memory_client = Memory.from_config(config)
                logger.info(
                    "Mem0 Memory client initialized on Qdrant collection '%s'",
                    settings.MEM0_COLLECTION_NAME,
                )
            except Exception as exc:
                logger.warning(
                    "Mem0 client initialization failed (%s). Memory will be inactive.",
                    exc,
                )
                self.enabled = False
                return None

        return self._memory_client

    async def add_user_preference(
        self,
        user_id: str,
        preference_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Store safe user preference (e.g. language or style), rejecting secrets."""
        if not self.enabled or not user_id:
            return None

        # Guard against storing secrets
        forbidden = ["bearer", "token", "password", "key", "secret"]
        if any(w in preference_text.lower() for w in forbidden):
            logger.warning("Rejected secret or token in memory preference text.")
            return {"status": "rejected", "reason": "Potential credential in memory"}

        client = self._get_client()
        if not client:
            return None

        try:
            res = client.add(
                preference_text,
                user_id=user_id,
                metadata=metadata or {},
            )
            return {"status": "success", "result": res}
        except Exception as exc:
            logger.warning("Failed to store memory for user %s: %s", user_id, exc)
            return None

    async def get_user_memories(
        self,
        user_id: str,
        query: str = "",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve memories strictly scoped by authenticated user_id."""
        if not self.enabled or not user_id:
            return []

        client = self._get_client()
        if not client:
            return []

        try:
            if query:
                results = client.search(query=query, user_id=user_id, limit=limit)
            else:
                results = client.get_all(user_id=user_id)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.warning("Failed to query memories for user %s: %s", user_id, exc)
            return []

    async def delete_user_memories(self, user_id: str) -> bool:
        """Erase all long-term memory for a user (GDPR / right to be forgotten)."""
        if not self.enabled or not user_id:
            return True

        client = self._get_client()
        if not client:
            return True

        try:
            client.delete_all(user_id=user_id)
            return True
        except Exception as exc:
            logger.warning("Failed to clear memories for user %s: %s", user_id, exc)
            return False
