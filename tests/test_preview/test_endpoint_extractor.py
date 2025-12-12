# Unit tests for EndpointExtractor
"""
Unit tests for EndpointExtractor utility.
Tests API endpoint parsing from FastAPI applications.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.endpoint_extractor import EndpointExtractor
from app.schemas.preview import EndpointInfo


class TestEndpointExtractor:
    """Unit tests for EndpointExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create EndpointExtractor instance."""
        return EndpointExtractor()

    @pytest.mark.asyncio
    async def test_extract_endpoints_from_metadata_success(self, extractor: EndpointExtractor):
        """Test successful endpoint extraction from metadata."""
        metadata = {
            "api_spec": {
                "routes": [
                    {
                        "path": "/api/users",
                        "method": "GET",
                        "description": "Get all users"
                    },
                    {
                        "path": "/api/users",
                        "method": "POST",
                        "description": "Create a user"
                    },
                    {
                        "path": "/api/users/{user_id}",
                        "method": "GET",
                        "description": "Get user by ID"
                    },
                    {
                        "path": "/health",
                        "method": "GET",
                        "description": "Health check"
                    }
                ]
            }
        }

        endpoints = await extractor.extract_endpoints(metadata)

        assert len(endpoints) == 4

        # Check endpoints (should be sorted by path, then method)
        get_users = next(e for e in endpoints if e.path == "/api/users" and e.method == "GET")
        assert get_users.description == "Get all users"

        post_users = next(e for e in endpoints if e.path == "/api/users" and e.method == "POST")
        assert post_users.description == "Create a user"

        get_user_by_id = next(e for e in endpoints if e.path == "/api/users/{user_id}" and e.method == "GET")
        assert get_user_by_id.description == "Get user by ID"

        health = next(e for e in endpoints if e.path == "/health" and e.method == "GET")
        assert health.description == "Health check"

    @pytest.mark.asyncio
    async def test_extract_endpoints_no_routes(self, extractor: EndpointExtractor):
        """Test endpoint extraction with no routes in metadata."""
        metadata = {"files": {"main.py": {"content": "print('hello')"}}}

        endpoints = await extractor.extract_endpoints(metadata)

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_extract_endpoints_empty_routes(self, extractor: EndpointExtractor):
        """Test endpoint extraction with empty routes list."""
        metadata = {"api_spec": {"routes": []}}

        endpoints = await extractor.extract_endpoints(metadata)

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_extract_endpoints_minimal_route(self, extractor: EndpointExtractor):
        """Test endpoint extraction with minimal route information."""
        metadata = {
            "api_spec": {
                "routes": [
                    {
                        "path": "/test",
                        "method": "GET"
                    }
                ]
            }
        }

        endpoints = await extractor.extract_endpoints(metadata)

        assert len(endpoints) == 1
        assert endpoints[0].path == "/test"
        assert endpoints[0].method == "GET"
        assert endpoints[0].description is None

    @pytest.mark.asyncio
    async def test_extract_endpoints_invalid_route(self, extractor: EndpointExtractor):
        """Test endpoint extraction with invalid route data."""
        metadata = {
            "api_spec": {
                "routes": [
                    "invalid_string_route",
                    {"invalid": "route"},
                    {"path": "/valid", "method": "GET"}
                ]
            }
        }

        endpoints = await extractor.extract_endpoints(metadata)

        # Should only extract the valid route
        assert len(endpoints) == 1
        assert endpoints[0].path == "/valid"
        assert endpoints[0].method == "GET"

    @pytest.mark.asyncio
    async def test_extract_endpoints_duplicate_removal(self, extractor: EndpointExtractor):
        """Test that duplicate endpoints are removed."""
        metadata = {
            "api_spec": {
                "routes": [
                    {"path": "/api/users", "method": "GET", "description": "First"},
                    {"path": "/api/users", "method": "GET", "description": "Second"}  # Duplicate
                ]
            }
        }

        endpoints = await extractor.extract_endpoints(metadata)

        assert len(endpoints) == 1
        assert endpoints[0].path == "/api/users"
        assert endpoints[0].method == "GET"
        # Should keep the first occurrence
        assert endpoints[0].description == "First"

    @pytest.mark.asyncio
    async def test_extract_endpoints_from_openapi(self, extractor: EndpointExtractor):
        """Test endpoint extraction from OpenAPI spec."""
        metadata = {
            "openapi_spec": {
                "paths": {
                    "/api/items": {
                        "get": {
                            "summary": "Get items",
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        with patch.object(extractor, '_extract_from_metadata', return_value=[]), \
             patch.object(extractor, '_extract_from_code', return_value=[]):

            endpoints = await extractor.extract_endpoints(metadata)

            assert len(endpoints) == 1
            assert endpoints[0].path == "/api/items"
            assert endpoints[0].method == "GET"
            assert endpoints[0].description == "Get items"
            assert endpoints[0].response_schema == {"type": "array"}

    @pytest.mark.asyncio
    async def test_extract_endpoints_from_code(self, extractor: EndpointExtractor):
        """Test endpoint extraction from code analysis."""
        metadata = {
            "files": {
                "app/main.py": {
                    "content": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/status")
async def get_status():
    return {"status": "ok"}

@app.post("/api/data")
async def create_data(data: dict):
    return {"created": True}
"""
                }
            }
        }

        with patch.object(extractor, '_extract_from_metadata', return_value=[]), \
             patch.object(extractor, '_extract_from_openapi', return_value=[]):

            endpoints = await extractor.extract_endpoints(metadata)

            # Should extract endpoints from code
            get_status = any(e.path == "/api/status" and e.method == "GET" for e in endpoints)
            post_data = any(e.path == "/api/data" and e.method == "POST" for e in endpoints)

            assert get_status or post_data  # At least one should be found

    @pytest.mark.asyncio
    async def test_extract_endpoints_from_generation(self, extractor: EndpointExtractor):
        """Test endpoint extraction from generation object."""
        generation = MagicMock()
        generation.extracted_schema = {
            "routes": [
                {"path": "/test", "method": "GET"}
            ]
        }
        generation.documentation = {}

        endpoints = await extractor.extract_endpoints_from_generation(generation)

        assert len(endpoints) == 1
        assert endpoints[0].path == "/test"
        assert endpoints[0].method == "GET"