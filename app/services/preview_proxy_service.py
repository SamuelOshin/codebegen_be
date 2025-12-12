# Preview proxy service
"""
HTTP proxy service for forwarding requests to preview instances.
Handles authentication, timeout, and error management.
"""

import httpx
from typing import Dict, Any, Optional
from loguru import logger


class PreviewProxyService:
    """
    Service for proxying HTTP requests to preview instances.

    Handles:
    - Request forwarding with proper headers
    - Timeout management
    - Error handling and response formatting
    - Authentication token validation
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize proxy service.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def proxy_request(
        self,
        base_url: str,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        preview_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Proxy an HTTP request to a preview instance.

        Args:
            base_url: Base URL of the preview instance
            method: HTTP method
            path: Request path
            query: Query parameters
            body: Request body
            headers: Request headers
            preview_token: Preview authentication token

        Returns:
            Response data with status code, data, and headers

        Raises:
            httpx.TimeoutException: Request timed out
            httpx.HTTPError: HTTP error occurred
            Exception: Other errors
        """
        url = f"{base_url.rstrip('/')}{path}"
        request_headers = dict(headers) if headers else {}

        # Remove preview token from forwarded headers for security
        request_headers.pop("X-Preview-Token", None)

        # Add any necessary headers
        if not request_headers.get("User-Agent"):
            request_headers["User-Agent"] = "CodeBEGen-Preview-Proxy/1.0"

        logger.debug(f"Proxying {method} {url} with query {query}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=query,
                    content=body,
                    headers=request_headers
                )

                # Format response
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }

                # Handle response body based on content type
                content_type = response.headers.get("content-type", "").lower()

                if content_type.startswith("application/json"):
                    try:
                        response_data["data"] = response.json()
                    except Exception:
                        # Fallback to text if JSON parsing fails
                        response_data["data"] = response.text
                else:
                    response_data["data"] = response.text

                logger.debug(f"Proxy response: {response.status_code} for {method} {url}")
                return response_data

        except httpx.TimeoutException as e:
            logger.warning(f"Proxy request timeout for {method} {url}: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Proxy HTTP error for {method} {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Proxy error for {method} {url}: {e}")
            raise

    async def health_check(self, base_url: str) -> bool:
        """
        Perform health check on preview instance.

        Args:
            base_url: Base URL of the preview instance

        Returns:
            True if healthy, False otherwise
        """
        try:
            health_url = f"{base_url.rstrip('/')}/health"
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except Exception:
            return False