import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Strict regex matching public GitHub repository URLs
# Captures: group(2) -> owner, group(3) -> repo
GITHUB_URL_REGEX = re.compile(
    r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
)


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidRepositoryURLError(GitHubError):
    """Raised when repository URL is malformed or not hosted on GitHub."""

    def __init__(self, message: str = "Invalid GitHub repository URL") -> None:
        super().__init__(message, status_code=400)


class RepositoryNotFoundError(GitHubError):
    """Raised when repository does not exist or is inaccessible."""

    def __init__(
        self,
        message: str = "Repository not found or is inaccessible on GitHub",
    ) -> None:
        super().__init__(message, status_code=404)


class RepositoryPrivateError(GitHubError):
    """Raised when repository is private (only public repositories supported)."""

    def __init__(
        self,
        message: str = (
            "Repository is private. Cortex currently only supports public repositories."
        ),
    ) -> None:
        super().__init__(message, status_code=400)


class RepositoryTooLargeError(GitHubError):
    """Raised when repository size exceeds configured maximum limit."""

    def __init__(self, size_mb: float, max_mb: int) -> None:
        msg = (
            f"Repository size ({size_mb:.1f} MB) exceeds maximum allowed limit "
            f"of {max_mb} MB"
        )
        super().__init__(msg, status_code=422)


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded. Please try again later.",
    ) -> None:
        super().__init__(message, status_code=429)


class GitHubService:
    """Service for validating and retrieving public GitHub repository metadata."""

    def __init__(
        self,
        token: str | None = None,
        max_size_mb: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.token = token or settings.GITHUB_TOKEN
        self.max_size_mb = max_size_mb or settings.MAX_REPO_SIZE_MB
        self._client = client

    @staticmethod
    def parse_github_url(url: str) -> tuple[str, str, str]:
        """Validate URL and extract (owner, repo, canonical_url).

        Raises InvalidRepositoryURLError on invalid format.
        """
        match = GITHUB_URL_REGEX.match(url.strip())
        if not match:
            raise InvalidRepositoryURLError(
                "Invalid GitHub URL. Must be in the format: "
                "https://github.com/owner/repository"
            )

        owner = match.group(1)
        repo = match.group(2)

        # Disallow root reserved GitHub paths
        reserved = {
            "settings",
            "explore",
            "trending",
            "topics",
            "collections",
            "organizations",
        }
        if owner.lower() in reserved or repo.lower() in reserved:
            raise InvalidRepositoryURLError(
                f"Invalid repository path: '{owner}/{repo}' is a reserved GitHub path"
            )

        canonical_url = f"https://github.com/{owner}/{repo}"
        return owner, repo, canonical_url

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Cortex-Codebase-RAG-App",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_repository_details(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """Fetch repository metadata and verify size limits and visibility."""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = self._get_headers()

        if self._client is not None:
            res = await self._client.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=headers)

        if res.status_code == 404:
            raise RepositoryNotFoundError(
                f"Repository '{owner}/{repo}' was not found on GitHub."
            )
        if res.status_code == 403 and "rate limit" in res.text.lower():
            raise GitHubRateLimitError()
        if res.status_code != 200:
            raise GitHubError(
                f"GitHub API error ({res.status_code}): {res.text[:200]}",
                status_code=res.status_code,
            )

        data = res.json()

        # Reject private repositories
        if data.get("private", False):
            raise RepositoryPrivateError()

        # Enforce size limits (GitHub API reports 'size' in KiB)
        size_kb = data.get("size", 0)
        size_mb = size_kb / 1024.0
        if size_mb > self.max_size_mb:
            raise RepositoryTooLargeError(size_mb, self.max_size_mb)

        default_branch = data.get("default_branch") or "main"

        return {
            "owner": data.get("owner", {}).get("login", owner),
            "name": data.get("name", repo),
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "description": data.get("description"),
            "default_branch": default_branch,
            "size_kb": size_kb,
            "stars": data.get("stargazers_count", 0),
        }

    async def get_latest_commit_sha(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> str:
        """Resolve the latest Git commit SHA for the target branch."""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        headers = self._get_headers()

        if self._client is not None:
            res = await self._client.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=headers)

        if res.status_code == 404:
            raise RepositoryNotFoundError(
                f"Branch '{branch}' was not found for '{owner}/{repo}'."
            )
        if res.status_code == 403 and "rate limit" in res.text.lower():
            raise GitHubRateLimitError()
        if res.status_code != 200:
            raise GitHubError(
                f"Failed to resolve latest commit SHA ({res.status_code})",
                status_code=res.status_code,
            )

        data = res.json()
        sha = data.get("sha")
        if not sha or not isinstance(sha, str) or len(sha) < 7:
            raise GitHubError("Invalid commit SHA received from GitHub")

        return sha
