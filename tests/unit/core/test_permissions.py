"""Unit tests for app/core/permissions.py"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID
from fastapi import HTTPException


class TestCheckKnowledgeBaseAccess:
    """Tests for check_knowledge_base_access function."""

    @pytest.mark.asyncio
    async def test_super_admin_has_access(self, sample_knowledge_base_id):
        """Should grant access to super_admin."""
        from app.core.permissions import check_knowledge_base_access

        result = await check_knowledge_base_access(
            user_id="user-123",
            knowledge_base_id=sample_knowledge_base_id,
            user_roles=["super_admin"],
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_admin_has_access(self, sample_knowledge_base_id):
        """Should grant access to admin."""
        from app.core.permissions import check_knowledge_base_access

        result = await check_knowledge_base_access(
            user_id="user-123",
            knowledge_base_id=sample_knowledge_base_id,
            user_roles=["admin"],
        )

        assert result is True

    @pytest.mark.asyncio
    @patch("app.core.permissions.get_db")
    async def test_owner_has_access(self, mock_get_db, sample_knowledge_base_id):
        """Should grant access to knowledge base owner."""
        from app.core.permissions import check_knowledge_base_access

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.count = 1
        mock_db.execute.return_value.fetchone.return_value = mock_result
        mock_get_db.return_value = iter([mock_db])

        result = await check_knowledge_base_access(
            user_id="owner-user",
            knowledge_base_id=sample_knowledge_base_id,
            user_roles=["user"],
        )

        assert result is True
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.permissions.get_db")
    async def test_non_owner_denied_access(self, mock_get_db, sample_knowledge_base_id):
        """Should deny access to non-owner without admin role."""
        from app.core.permissions import check_knowledge_base_access

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.count = 0
        mock_db.execute.return_value.fetchone.return_value = mock_result
        mock_get_db.return_value = iter([mock_db])

        result = await check_knowledge_base_access(
            user_id="other-user",
            knowledge_base_id=sample_knowledge_base_id,
            user_roles=["user"],
        )

        assert result is False
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.permissions.get_db")
    async def test_database_error_returns_false(self, mock_get_db, sample_knowledge_base_id):
        """Should return False on database error."""
        from app.core.permissions import check_knowledge_base_access

        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database error")
        mock_get_db.return_value = iter([mock_db])

        result = await check_knowledge_base_access(
            user_id="user-123",
            knowledge_base_id=sample_knowledge_base_id,
            user_roles=["user"],
        )

        assert result is False


class TestRequireKnowledgeBaseAccess:
    """Tests for require_knowledge_base_access function."""

    @pytest.mark.asyncio
    async def test_missing_user_id_raises_401(self, sample_knowledge_base_id):
        """Should raise 401 when user_id is missing."""
        from app.core.permissions import require_knowledge_base_access

        payload = {"roles": ["user"]}

        with pytest.raises(HTTPException) as exc_info:
            await require_knowledge_base_access(payload, sample_knowledge_base_id)

        assert exc_info.value.status_code == 401
        assert "missing user_id" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.core.permissions.check_knowledge_base_access")
    async def test_no_access_raises_403(self, mock_check, sample_knowledge_base_id):
        """Should raise 403 when user has no access."""
        from app.core.permissions import require_knowledge_base_access

        mock_check.return_value = False
        payload = {"sub": "user-123", "roles": ["user"]}

        with pytest.raises(HTTPException) as exc_info:
            await require_knowledge_base_access(payload, sample_knowledge_base_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.core.permissions.check_knowledge_base_access")
    async def test_valid_access_passes(self, mock_check, sample_knowledge_base_id):
        """Should not raise when user has access."""
        from app.core.permissions import require_knowledge_base_access

        mock_check.return_value = True
        payload = {"sub": "user-123", "roles": ["admin"]}

        # Should not raise
        await require_knowledge_base_access(payload, sample_knowledge_base_id)

        mock_check.assert_called_once()
