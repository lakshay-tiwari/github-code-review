"""
Lightweight question intent classifier for codebase RAG retrieval.

Classifies questions without any LLM call or network access, using
deterministic regex / keyword matching. Classification is used by the
retrieval node to tune vector search parameters per intent level.

Intent levels
─────────────
file_specific   – question refers to a single file by path or extension
symbol_specific – question refers to a named function, class, method, or
                  variable by identifier
workflow        – question asks about a process, flow, or interaction that
                  likely spans several related components in the same area
repository_wide – question asks about overall architecture, all X, how the
                  system works, etc. — needs broad multi-file coverage
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Pattern sets (most specific → least specific, evaluated in order)
# ---------------------------------------------------------------------------

# File-specific: mentions a file path or extension explicitly
_FILE_PATTERNS = [
    re.compile(r"\b[\w/\-]+\.\w{2,6}\b"),          # word.ext (at least 2-char ext)
    re.compile(r"\bin\s+(the\s+)?file\b", re.I),
    re.compile(r"\bfile\s+path\b", re.I),
]

# Symbol-specific: refers to a specific named code entity
_SYMBOL_PATTERNS = [
    re.compile(r"\bfunction\s+\w+\b", re.I),
    re.compile(r"\bmethod\s+\w+\b", re.I),
    re.compile(r"\bclass\s+\w+\b", re.I),
    re.compile(r"\b\w+\(\)\b"),                      # call-syntax: foo()
    re.compile(r"\bdef\s+\w+\b", re.I),
    re.compile(r"\bwhat\s+does\s+\w+\s+do\b", re.I),
    re.compile(r"\bwhat\s+does\s+\w+\(\)", re.I),
    re.compile(r"\bhow\s+does\s+\w+\(\)", re.I),
    re.compile(r"\bexplain\s+\w+\(\)", re.I),
    re.compile(r"\btrace\s+\w+\b", re.I),
    re.compile(r"\bwhat\s+does\s+\w+\s+return\b", re.I),
]

# Workflow: process, pipeline, end-to-end but scoped (not whole-repo).
# Use whole-word matching to prevent "process_data" triggering "process".
_WORKFLOW_REGEXES = [
    re.compile(r"\bflow\b", re.I),
    re.compile(r"\bpipeline\b", re.I),
    re.compile(r"\blifecycle\b", re.I),
    re.compile(r"\bsequence\b", re.I),
    re.compile(r"\bhow\s+does\b", re.I),
    re.compile(r"\bstep\s+by\s+step\b", re.I),
    re.compile(r"\bworkflow\b", re.I),
    re.compile(r"\bend[-\s]to[-\s]end\b", re.I),
    re.compile(r"\bwalkthrough\b", re.I),
    re.compile(r"\brequest\s+lifecycle\b", re.I),
    re.compile(r"\bresponse\s+cycle\b", re.I),
    re.compile(r"\bprocess\b", re.I),  # whole-word only
]

# Repository-wide: whole-system questions
_REPO_WIDE_REGEXES = [
    re.compile(r"\barchitecture\b", re.I),
    re.compile(r"\boverview\b", re.I),
    re.compile(r"\bstructure\b", re.I),
    re.compile(r"\bentire\b", re.I),
    re.compile(r"\bwhole\b", re.I),
    re.compile(r"\ball\s+files\b", re.I),
    re.compile(r"\ball\s+modules\b", re.I),
    re.compile(r"\ball\s+endpoints\b", re.I),
    re.compile(r"\bhow\s+is\s+this\s+repo\b", re.I),
    re.compile(r"\bhow\s+is\s+this\s+project\b", re.I),
    re.compile(r"\bwhat\s+does\s+this\s+project\b", re.I),
    re.compile(r"\bwhat\s+does\s+this\s+repo\b", re.I),
    re.compile(r"\bcodebase\b", re.I),
    re.compile(r"\bproject\s+layout\b", re.I),
    re.compile(r"\btop[-\s]level\b", re.I),
    re.compile(r"\bbig\s+picture\b", re.I),
    re.compile(r"\bhigh[-\s]level\b", re.I),
    re.compile(r"\blist\s+all\b", re.I),
    re.compile(r"\blist\s+every\b", re.I),
]


def classify_question(question: str) -> str:
    """Return one of: 'file_specific', 'symbol_specific', 'workflow', 'repository_wide'.

    Evaluation order guarantees the most specific match wins.
    """
    # 1. File-specific
    if any(pat.search(question) for pat in _FILE_PATTERNS):
        return "file_specific"

    # 2. Symbol-specific — checked before workflow so "what does X return?" wins
    if any(pat.search(question) for pat in _SYMBOL_PATTERNS):
        return "symbol_specific"

    # 3. Repository-wide (most general, checked before workflow)
    if any(pat.search(question) for pat in _REPO_WIDE_REGEXES):
        return "repository_wide"

    # 4. Workflow — "process" only matches if the WHOLE word is "process", not
    #    part of an identifier, because we use \bprocess\b in the regex.
    if any(pat.search(question) for pat in _WORKFLOW_REGEXES):
        return "workflow"

    # Default: treat as symbol-specific (best single-focus retrieval behaviour)
    return "symbol_specific"


# Retrieval parameter presets keyed by intent
RETRIEVAL_PRESETS: dict[str, dict] = {
    "file_specific": {
        "limit": 12,
        "score_threshold": 0.25,
        "expansion_limit": 20,
        "min_chunks_for_expansion": 2,
        "required_distinct_files": 1,
    },
    "symbol_specific": {
        "limit": 8,
        "score_threshold": 0.30,
        "expansion_limit": 14,
        "min_chunks_for_expansion": 2,
        "required_distinct_files": 1,
    },
    "workflow": {
        "limit": 14,
        "score_threshold": 0.25,
        "expansion_limit": 24,
        "min_chunks_for_expansion": 3,
        "required_distinct_files": 2,
    },
    "repository_wide": {
        "limit": 20,
        "score_threshold": 0.20,
        "expansion_limit": 35,
        "min_chunks_for_expansion": 4,
        "required_distinct_files": 2,
    },
}
