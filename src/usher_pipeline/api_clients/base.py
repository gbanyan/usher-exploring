"""Base API client with retry logic and persistent caching."""

import logging
import time
from pathlib import Path
from typing import Any

import requests
import requests_cache
from requests.exceptions import ConnectionError, HTTPError, Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from usher_pipeline.config.schema import PipelineConfig

logger = logging.getLogger(__name__)


class CachedAPIClient:
    """
    HTTP client with rate limiting, retry logic, and persistent SQLite caching.

    Features:
    - Automatic retry on 429/5xx/network errors with exponential backoff
    - Persistent SQLite cache with configurable TTL
    - Rate limiting to avoid overwhelming APIs
    - Cache statistics tracking
    """

    def __init__(
        self,
        cache_dir: Path,
        rate_limit: int = 5,
        max_retries: int = 5,
        cache_ttl: int = 86400,
        timeout: int = 30,
    ):
        """
        Initialize API client with caching and retry logic.

        Args:
            cache_dir: Directory for SQLite cache storage
            rate_limit: Maximum requests per second
            max_retries: Maximum retry attempts on failure
            cache_ttl: Cache time-to-live in seconds (0 = infinite)
            timeout: Request timeout in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize requests_cache session
        cache_path = self.cache_dir / "api_cache"
        expire_after = cache_ttl if cache_ttl > 0 else None

        self.session = requests_cache.CachedSession(
            cache_name=str(cache_path),
            backend="sqlite",
            expire_after=expire_after,
        )

    def _should_rate_limit(self, response: requests.Response) -> bool:
        """Check if response came from cache (no rate limit needed)."""
        return not getattr(response, "from_cache", False)

    def _create_retry_decorator(self):
        """Create retry decorator with exponential backoff."""
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=60),
            retry=retry_if_exception_type((HTTPError, Timeout, ConnectionError)),
            reraise=True,
        )

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> requests.Response:
        """
        Make GET request with retry logic and caching.

        Args:
            url: Request URL
            params: Query parameters
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            HTTPError: On HTTP error after retries exhausted
            Timeout: On timeout after retries exhausted
            ConnectionError: On connection error after retries exhausted
        """
        # Apply retry decorator dynamically
        @self._create_retry_decorator()
        def _get_with_retry():
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )

            # Check for HTTP errors
            try:
                response.raise_for_status()
            except HTTPError as e:
                # Log warning for rate limiting
                if response.status_code == 429:
                    logger.warning(
                        f"Rate limited by API (429). "
                        f"URL: {url}. Will retry with backoff."
                    )
                raise e

            return response

        # Make request with retry
        response = _get_with_retry()

        # Rate limit only non-cached requests
        if self._should_rate_limit(response):
            time.sleep(1 / self.rate_limit)

        return response

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make GET request and return JSON response.

        Args:
            url: Request URL
            params: Query parameters
            **kwargs: Additional arguments passed to requests

        Returns:
            Parsed JSON response as dict

        Raises:
            HTTPError: On HTTP error
            JSONDecodeError: If response is not valid JSON
        """
        response = self.get(url, params=params, **kwargs)
        return response.json()

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "CachedAPIClient":
        """
        Create client from pipeline configuration.

        Args:
            config: PipelineConfig instance

        Returns:
            Configured CachedAPIClient instance
        """
        return cls(
            cache_dir=config.cache_dir,
            rate_limit=config.api.rate_limit_per_second,
            max_retries=config.api.max_retries,
            cache_ttl=config.api.cache_ttl_seconds,
            timeout=config.api.timeout_seconds,
        )

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self.session.cache.clear()
        logger.info("API cache cleared")

    def cache_stats(self) -> dict[str, Any]:
        """
        Get cache hit/miss statistics.

        Returns:
            Dictionary with cache statistics
        """
        # requests_cache doesn't provide built-in stats,
        # so we return basic info about cache state
        cache_path = self.cache_dir / "api_cache.sqlite"

        stats = {
            "cache_enabled": True,
            "cache_path": str(cache_path),
            "cache_exists": cache_path.exists(),
        }

        # Get cache size if it exists
        if cache_path.exists():
            stats["cache_size_bytes"] = cache_path.stat().st_size

        return stats
