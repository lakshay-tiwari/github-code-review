import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns indicative of prompt injection attempts embedded in code or comments
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(secret|password|api[_\s]key)", re.IGNORECASE),
    re.compile(r"delete\s+all\s+(data|users|records)", re.IGNORECASE),
]

# Sensitive credentials that must never be exposed or accepted
SECRET_PATTERNS = [
    re.compile(r"(ghp_[A-Za-z0-9_]{36}|github_pat_[A-Za-z0-9_]{82})"),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"gsk_[A-Za-z0-9]{48}"),
    re.compile(r"sk-[A-Za-z0-9]{48}"),
]


class GuardrailViolation(Exception):
    """Raised when an active guardrail condition is violated."""


class RAGGuardrails:
    """Application-level safety controls for RAG retrieval, citations, and prompts."""

    @staticmethod
    def sanitize_untrusted_code(code_text: str) -> str:
        """Neutralize malicious injection instructions in repository code."""
        sanitized = code_text
        for pattern in INJECTION_PATTERNS:
            if pattern.search(sanitized):
                logger.warning(
                    "Neutralized potential prompt injection in repository content."
                )
                sanitized = pattern.sub("[FLAGGED_INSTRUCTION_REMOVED]", sanitized)
        return sanitized

    @staticmethod
    def inspect_for_secret_leakage(text: str) -> str:
        """Mask potential secrets and tokens from being emitted in answers."""
        masked = text
        for pattern in SECRET_PATTERNS:
            if pattern.search(masked):
                logger.warning("Masked potential credential or secret in response.")
                masked = pattern.sub("[REDACTED_SECRET]", masked)
        return masked

    @staticmethod
    def validate_citation_evidence(
        citation: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> bool:
        """Verify that a cited file path and line numbers exist in retrieved chunks."""
        file_path = citation.get("file_path")
        start_line = citation.get("start_line")
        end_line = citation.get("end_line")

        if not file_path or start_line is None or end_line is None:
            return False

        for chunk in retrieved_chunks:
            if chunk.get("file_path") == file_path:
                chunk_start = chunk.get("start_line", 0)
                chunk_end = chunk.get("end_line", 0)
                # Overlap check
                if not (end_line < chunk_start or start_line > chunk_end):
                    return True
        return False
