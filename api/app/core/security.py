import asyncio
import logging
import time
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("cortex.security")


class UserContext(BaseModel):
    """Trusted user identity context derived strictly from verified JWT claims."""

    user_id: str
    session_id: str | None = None
    email: str | None = None
    authorized_party: str | None = None
    claims: dict[str, Any] = Field(default_factory=dict)


class ClerkAuthenticationError(Exception):
    """Raised when Clerk JWT verification fails."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ClerkTokenVerifier:
    """Verifies Clerk asymmetric JWT session tokens against JWKS or PEM public key.

    Implements:
    - RS256 signature verification.
    - Standard claims verification (exp, nbf, iat, sub).
    - Issuer check against settings.clerk_effective_issuer.
    - Authorized party (azp) verification if configured.
    - In-memory caching of JWKS public keys with refresh on unknown kid.
    - Zero token logging and zero raw token persistence.
    """

    def __init__(
        self,
        jwks_url: str | None = None,
        expected_issuer: str | None = None,
        expected_audience: str | None = None,
        expected_azp: str | None = None,
        pem_public_key: str | None = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self.jwks_url = jwks_url or settings.clerk_effective_jwks_url
        self.expected_issuer = expected_issuer or settings.clerk_effective_issuer
        self.expected_audience = expected_audience or settings.CLERK_AUDIENCE or None
        self.expected_azp = expected_azp or settings.CLERK_AUTHORIZED_PARTY or None
        self.pem_public_key = pem_public_key or settings.CLERK_PEM_PUBLIC_KEY or None
        self.cache_ttl = cache_ttl_seconds

        self._keys_cache: dict[str, RSAPublicKey] = {}
        self._cache_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def _fetch_jwks_keys(self) -> dict[str, RSAPublicKey]:
        """Fetch and parse JWKS keys from the Clerk JWKS endpoint."""
        if not self.jwks_url:
            raise ClerkAuthenticationError("Clerk JWKS URL is not configured")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                if response.status_code != 200:
                    logger.error(
                        "Failed to fetch Clerk JWKS: HTTP %s", response.status_code
                    )
                    raise ClerkAuthenticationError(
                        "Unable to retrieve authentication public keys"
                    )
                data = response.json()
        except httpx.RequestError as exc:
            logger.error("Network error fetching Clerk JWKS: %s", type(exc).__name__)
            raise ClerkAuthenticationError(
                "Authentication service temporarily unavailable"
            ) from exc

        keys_list = data.get("keys", [])
        parsed_keys: dict[str, RSAPublicKey] = {}
        for key_dict in keys_list:
            kid = key_dict.get("kid")
            if kid and key_dict.get("kty") == "RSA":
                try:
                    public_key = RSAAlgorithm.from_jwk(key_dict)
                    if isinstance(public_key, RSAPublicKey):
                        parsed_keys[kid] = public_key
                except Exception as parse_err:
                    logger.warning(
                        "Skipping unparseable JWK with kid %s: %s",
                        kid,
                        type(parse_err).__name__,
                    )

        if not parsed_keys:
            raise ClerkAuthenticationError("No valid RSA keys found in Clerk JWKS")

        return parsed_keys

    async def get_public_key(self, kid: str | None) -> RSAPublicKey:
        """Resolve the appropriate RSA public key for signature verification."""
        if self.pem_public_key:
            try:
                key = serialization.load_pem_public_key(
                    self.pem_public_key.encode("utf-8")
                )
                if isinstance(key, RSAPublicKey):
                    return key
                raise ClerkAuthenticationError(
                    "Configured PEM key is not an RSA public key"
                )
            except Exception as err:
                raise ClerkAuthenticationError(
                    "Invalid PEM public key configuration"
                ) from err

        if not kid:
            raise ClerkAuthenticationError("Token missing 'kid' in header")

        now = time.time()
        # Fast read from in-memory cache
        if now < self._cache_expires_at and kid in self._keys_cache:
            return self._keys_cache[kid]

        # Acquire lock to refresh cache
        async with self._lock:
            # Recheck inside lock
            if time.time() < self._cache_expires_at and kid in self._keys_cache:
                return self._keys_cache[kid]

            fresh_keys = await self._fetch_jwks_keys()
            self._keys_cache = fresh_keys
            self._cache_expires_at = time.time() + self.cache_ttl

            if kid in self._keys_cache:
                return self._keys_cache[kid]

            raise ClerkAuthenticationError("Signing key not found in Clerk JWKS")

    async def verify_token(self, token: str) -> UserContext:
        """Verify the session token and return a trusted UserContext."""
        if not token or not isinstance(token, str):
            raise ClerkAuthenticationError("Empty or invalid token format")

        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception:
            raise ClerkAuthenticationError("Malformed token header")

        alg = unverified_header.get("alg")
        if alg != "RS256":
            raise ClerkAuthenticationError(
                "Unsupported algorithm; only RS256 is accepted"
            )

        kid = unverified_header.get("kid")
        public_key = await self.get_public_key(kid)

        try:
            payload = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "require": ["exp", "iat", "sub"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
                leeway=10,
                issuer=self.expected_issuer if self.expected_issuer else None,
                audience=self.expected_audience if self.expected_audience else None,
            )
        except jwt.ExpiredSignatureError:
            raise ClerkAuthenticationError("Token has expired")
        except jwt.ImmatureSignatureError:
            raise ClerkAuthenticationError("Token is not yet active (nbf)")
        except jwt.InvalidIssuerError:
            raise ClerkAuthenticationError("Invalid token issuer")
        except jwt.InvalidAudienceError:
            raise ClerkAuthenticationError("Invalid token audience")
        except jwt.InvalidSignatureError:
            raise ClerkAuthenticationError("Invalid token signature")
        except jwt.InvalidTokenError:
            raise ClerkAuthenticationError("Invalid authentication token")

        # Validate authorized party (azp) if configured
        if self.expected_azp:
            azp = payload.get("azp")
            if azp != self.expected_azp:
                raise ClerkAuthenticationError("Invalid authorized party (azp)")

        user_id = payload.get("sub")
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ClerkAuthenticationError("Token missing valid subject (sub)")

        return UserContext(
            user_id=user_id,
            session_id=payload.get("sid"),
            email=payload.get("email"),
            authorized_party=payload.get("azp"),
            claims={k: v for k, v in payload.items() if k not in ("token", "secret")},
        )


# Global singleton verifier
_verifier_instance: ClerkTokenVerifier | None = None


def get_token_verifier() -> ClerkTokenVerifier:
    """Return the application singleton ClerkTokenVerifier."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = ClerkTokenVerifier()
    return _verifier_instance
