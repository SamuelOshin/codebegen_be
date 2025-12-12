# Endpoint extractor for generated APIs
"""
Utility for extracting endpoint information from generated FastAPI applications.
Parses generation metadata and code to discover available API endpoints.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.schemas.preview import EndpointInfo


class EndpointExtractor:
    """
    Extracts endpoint information from generated FastAPI applications.

    Supports multiple methods:
    1. Parse OpenAPI/Swagger spec if available
    2. Parse FastAPI route decorators from code
    3. Extract from generation metadata
    """

    def __init__(self):
        """Initialize endpoint extractor."""
        pass

    async def extract_endpoints(self, generation_metadata: Dict[str, Any]) -> List[EndpointInfo]:
        """
        Extract endpoints from generation metadata.

        Args:
            generation_metadata: Generation metadata dictionary

        Returns:
            List of endpoint information
        """
        endpoints = []

        # Try different extraction methods
        endpoints.extend(self._extract_from_metadata(generation_metadata))
        endpoints.extend(await self._extract_from_openapi(generation_metadata))
        endpoints.extend(await self._extract_from_code(generation_metadata))

        # Remove duplicates and sort
        unique_endpoints = self._deduplicate_endpoints(endpoints)
        return sorted(unique_endpoints, key=lambda x: (x.path, x.method))

    def _extract_from_metadata(self, metadata: Dict[str, Any]) -> List[EndpointInfo]:
        """
        Extract endpoints from generation metadata.

        Args:
            metadata: Generation metadata

        Returns:
            List of endpoints from metadata
        """
        endpoints = []

        # Look for endpoints in various metadata fields
        api_spec = metadata.get("api_spec", {})
        routes = api_spec.get("routes", [])

        for route in routes:
            if isinstance(route, dict) and "path" in route and "method" in route:
                endpoint = EndpointInfo(
                    method=route.get("method", "GET"),
                    path=route.get("path", ""),
                    description=route.get("description"),
                    request_schema=route.get("request_schema"),
                    response_schema=route.get("response_schema")
                )
                endpoints.append(endpoint)

        return endpoints

    async def _extract_from_openapi(self, metadata: Dict[str, Any]) -> List[EndpointInfo]:
        """
        Extract endpoints from OpenAPI/Swagger specification.

        Args:
            metadata: Generation metadata

        Returns:
            List of endpoints from OpenAPI spec
        """
        endpoints = []

        # Look for OpenAPI spec in metadata
        openapi_spec = metadata.get("openapi_spec", {})
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            if isinstance(methods, dict):
                for method, spec in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        endpoint = EndpointInfo(
                            method=method.upper(),
                            path=path,
                            description=spec.get("summary") or spec.get("description"),
                            request_schema=spec.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema"),
                            response_schema=self._extract_response_schema(spec.get("responses", {}))
                        )
                        endpoints.append(endpoint)

        return endpoints

    async def _extract_from_code(self, metadata: Dict[str, Any]) -> List[EndpointInfo]:
        """
        Extract endpoints by parsing generated code.

        Args:
            metadata: Generation metadata

        Returns:
            List of endpoints from code analysis
        """
        endpoints = []

        # Get main.py content from metadata or storage
        main_file = metadata.get("files", {}).get("app/main.py")
        if not main_file:
            return endpoints

        # Handle both string content and dict with content key
        if isinstance(main_file, dict):
            main_content = main_file.get("content", "")
        else:
            main_content = main_file

        if not main_content:
            return endpoints

        # Parse FastAPI route decorators
        route_pattern = r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        matches = re.findall(route_pattern, main_content, re.IGNORECASE | re.MULTILINE)

        for method, path in matches:
            # Try to extract function docstring for description
            func_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\'|(?:\n\s*"""(.*?)"""))'
            func_matches = re.findall(func_pattern, main_content[main_content.find(f'@{method.lower()}("{path}")'):], re.DOTALL)

            description = None
            if func_matches:
                # Take the first docstring found
                for match in func_matches[0][1:]:
                    if match.strip():
                        description = match.strip()
                        break

            endpoint = EndpointInfo(
                method=method.upper(),
                path=path,
                description=description
            )
            endpoints.append(endpoint)

        return endpoints

    def _extract_response_schema(self, responses: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract response schema from OpenAPI responses.

        Args:
            responses: OpenAPI responses object

        Returns:
            Response schema or None
        """
        # Look for 200 response first, then default
        for status in ["200", "default"]:
            if status in responses:
                response = responses[status]
                content = response.get("content", {})
                json_content = content.get("application/json", {})
                return json_content.get("schema")

        return None

    def _deduplicate_endpoints(self, endpoints: List[EndpointInfo]) -> List[EndpointInfo]:
        """
        Remove duplicate endpoints based on method and path.

        Args:
            endpoints: List of endpoints

        Returns:
            Deduplicated list
        """
        seen = set()
        unique_endpoints = []

        for endpoint in endpoints:
            key = (endpoint.method, endpoint.path)
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(endpoint)

        return unique_endpoints

    async def extract_endpoints_from_generation(self, generation) -> List[EndpointInfo]:
        """
        Extract endpoints from a Generation model instance.

        Args:
            generation: Generation model instance

        Returns:
            List of endpoint information
        """
        # Build metadata from generation fields
        metadata = {
            "api_spec": generation.extracted_schema or {},
            "openapi_spec": generation.documentation or {},
            "files": {}  # Would need to load from storage if needed
        }

        return await self.extract_endpoints(metadata)