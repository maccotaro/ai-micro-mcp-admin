"""権限チェックモジュール"""
import logging
from uuid import UUID
from typing import Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.core.database import get_db

logger = logging.getLogger(__name__)


async def check_knowledge_base_access(
    user_id: str,
    knowledge_base_id: UUID,
    user_roles: list
) -> bool:
    """ナレッジベースへのアクセス権限をチェック"""

    # super_adminは全アクセス可能
    if "super_admin" in user_roles or "admin" in user_roles:
        logger.info(f"Admin user {user_id} granted access to KB {knowledge_base_id}")
        return True

    # データベースで権限確認
    db = next(get_db())
    try:
        query = text("""
            SELECT COUNT(*) as count
            FROM knowledge_bases kb
            WHERE kb.id = :kb_id
              AND (
                kb.created_by = :user_id
                OR kb.is_public = true
              )
        """)

        result = db.execute(
            query,
            {"kb_id": str(knowledge_base_id), "user_id": user_id}
        ).fetchone()

        has_access = result.count > 0

        if has_access:
            logger.info(f"User {user_id} has access to KB {knowledge_base_id}")
        else:
            logger.warning(f"User {user_id} denied access to KB {knowledge_base_id}")

        return has_access

    except Exception as e:
        logger.error(f"Error checking KB access: {e}")
        return False
    finally:
        db.close()


async def require_knowledge_base_access(
    payload: Dict[str, Any],
    knowledge_base_id: UUID
):
    """ナレッジベースアクセス権限を要求（権限なしで403例外）"""

    user_id = payload.get("sub")
    user_roles = payload.get("roles", [])

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id"
        )

    # 権限チェック（非同期呼び出し）
    has_access = await check_knowledge_base_access(
        user_id, knowledge_base_id, user_roles
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to knowledge base {knowledge_base_id}"
        )
