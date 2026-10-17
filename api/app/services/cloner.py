import io
import logging
import os
import tarfile

import httpx

from app.core.config import settings
from app.services.github import GitHubError, GitHubRateLimitError

logger = logging.getLogger(__name__)


class ClonerError(Exception):
    """Base exception for repository cloning and extraction."""

    pass


class RepositoryCloner:
    """Safely downloads and extracts repository archives pinned to a Git commit SHA."""

    def __init__(
        self,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.token = token or settings.GITHUB_TOKEN
        self._client = client

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Cortex-Codebase-RAG-App",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def download_and_extract_tarball(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
        destination_dir: str,
    ) -> str:
        """Download GitHub tarball for the commit SHA and extract safely.

        Uses Python 3.12 tarfile data_filter to prevent directory traversal / zip slip.
        Returns the path to the root directory containing extracted files.
        """
        tarball_url = (
            f"https://api.github.com/repos/{owner}/{repo}/tarball/{commit_sha}"
        )
        headers = self._get_headers()

        logger.info(
            "Downloading repository archive for %s/%s at commit %s",
            owner,
            repo,
            commit_sha,
        )

        try:
            if self._client is not None:
                res = await self._client.get(
                    tarball_url, headers=headers, follow_redirects=True
                )
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.get(
                        tarball_url, headers=headers, follow_redirects=True
                    )

            if res.status_code == 403 and "rate limit" in res.text.lower():
                raise GitHubRateLimitError()
            if res.status_code != 200:
                raise GitHubError(
                    f"Failed to download repository archive ({res.status_code}): "
                    f"{res.text[:200]}",
                    status_code=res.status_code,
                )

            # Extract tarball in memory using tarfile data_filter
            with tarfile.open(fileobj=io.BytesIO(res.content), mode="r:*") as tar:
                # Python 3.12 data_filter protects against directory traversal
                tar.extractall(path=destination_dir, filter="data")

        except Exception as exc:
            if isinstance(exc, (GitHubError, ClonerError)):
                raise
            raise ClonerError(f"Failed to extract repository archive: {exc}") from exc

        # GitHub tarballs create a single top-level directory like: owner-repo-sha/
        subdirs = [
            os.path.join(destination_dir, d)
            for d in os.listdir(destination_dir)
            if os.path.isdir(os.path.join(destination_dir, d))
        ]

        if len(subdirs) == 1:
            return subdirs[0]
        return destination_dir
