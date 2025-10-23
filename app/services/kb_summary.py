"""ナレッジベースサマリーサービス"""
import logging
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import text
from app.core.database import get_db

logger = logging.getLogger(__name__)


class KBSummaryService:
    """ナレッジベースサマリーサービス"""

    async def get_summary(self, knowledge_base_id: UUID) -> Dict[str, Any]:
        """ナレッジベースのサマリーを取得"""

        db = next(get_db())
        try:
            # サマリーデータを取得
            query = text("""
                SELECT
                    kb.name,
                    kb.description,
                    COUNT(DISTINCT c.id) as total_collections,
                    COUNT(DISTINCT d.id) as total_documents,
                    COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM knowledge_bases kb
                LEFT JOIN collections c ON c.knowledge_base_id = kb.id
                LEFT JOIN documents d ON d.collection_id = c.id
                WHERE kb.id = :kb_id
                GROUP BY kb.id, kb.name, kb.description
            """)

            result = db.execute(
                query,
                {"kb_id": str(knowledge_base_id)}
            ).fetchone()

            if not result:
                raise ValueError(f"Knowledge base {knowledge_base_id} not found")

            return {
                "name": result.name,
                "description": result.description or "",
                "summary_text": f"{result.name}の概要情報",
                "total_collections": result.total_collections,
                "total_documents": result.total_documents,
                "total_chunks": result.total_chunks,
                "key_topics": [],
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting KB summary: {e}")
            raise
        finally:
            # 接続を確実にクローズ（接続リーク防止）
            db.close()
