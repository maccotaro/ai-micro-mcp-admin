"""Shared fixtures for mcp-admin tests."""
import os
import pytest
from unittest.mock import MagicMock
from uuid import UUID

# Set test environment variables
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:password@localhost:5432/testdb")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("EMBEDDING_MODEL", "embeddinggemma:300m")
os.environ.setdefault("JWKS_URL", "http://localhost:8002/.well-known/jwks.json")
os.environ.setdefault("JWT_ALGORITHM", "RS256")


@pytest.fixture
def sample_user_payload():
    """Sample JWT payload for authenticated user."""
    return {
        "sub": "test-user-123",
        "roles": ["user"],
        "tenant_id": "test-tenant-id",
        "exp": 9999999999,
        "iat": 1234567890,
    }


@pytest.fixture
def sample_admin_payload():
    """Sample JWT payload for admin user."""
    return {
        "sub": "admin-user-456",
        "roles": ["admin", "user"],
        "tenant_id": "test-tenant-id",
        "exp": 9999999999,
        "iat": 1234567890,
    }


@pytest.fixture
def sample_super_admin_payload():
    """Sample JWT payload for super admin user."""
    return {
        "sub": "super-admin-789",
        "roles": ["super_admin", "admin", "user"],
        "tenant_id": "test-tenant-id",
        "exp": 9999999999,
        "iat": 1234567890,
    }


@pytest.fixture
def sample_knowledge_base_id():
    """Sample knowledge base UUID."""
    return UUID("9fba1ff9-3159-4417-a5d1-cf6a079c3a1b")
