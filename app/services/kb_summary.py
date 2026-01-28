"""ナレッジベースサマリーサービス"""
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import text
from app.core.database import get_db

logger = logging.getLogger(__name__)


class KBSummaryService:
    """ナレッジベースサマリーサービス"""

    async def get_summary(self, knowledge_base_id: UUID) -> Dict[str, Any]:
        """ナレッジベースのサマリーを取得

        description を単一ソースとして使用。
        meta_topics, meta_keywords があれば検索参考情報として付加。
        """

        db = next(get_db())
        try:
            # KB基本情報と統計を取得（description, meta_topics, meta_keywords 含む）
            stats_query = text("""
                SELECT
                    kb.name,
                    kb.description,
                    kb.meta_topics,
                    kb.meta_keywords,
                    kb.updated_at,
                    COUNT(DISTINCT c.id) as total_collections,
                    COUNT(DISTINCT d.id) as total_documents,
                    COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM knowledge_bases kb
                LEFT JOIN collections c ON c.knowledge_base_id = kb.id
                LEFT JOIN documents d ON d.collection_id = c.id
                WHERE kb.id = :kb_id
                GROUP BY kb.id, kb.name, kb.description, kb.meta_topics, kb.meta_keywords, kb.updated_at
            """)

            stats_result = db.execute(
                stats_query,
                {"kb_id": str(knowledge_base_id)}
            ).fetchone()

            if not stats_result:
                raise ValueError(f"Knowledge base {knowledge_base_id} not found")

            # コレクション名を取得（「含まれるコレクション」として使用）
            collections_query = text("""
                SELECT name FROM collections
                WHERE knowledge_base_id = :kb_id
                ORDER BY created_at DESC
            """)

            collections_result = db.execute(
                collections_query,
                {"kb_id": str(knowledge_base_id)}
            ).fetchall()

            collection_names = [row[0] for row in collections_result] if collections_result else []

            # meta_topics: LLM抽出の主要トピック（「主要トピック」として使用）
            meta_topics = []
            if stats_result.meta_topics:
                meta_topics = stats_result.meta_topics if isinstance(stats_result.meta_topics, list) else list(stats_result.meta_topics)

            # サマリーテキストを生成（description + 統計情報 + コレクション名 + 主要トピック）
            summary_text = self._generate_default_summary(
                name=stats_result.name,
                description=stats_result.description,
                total_collections=stats_result.total_collections,
                total_documents=stats_result.total_documents,
                total_chunks=stats_result.total_chunks,
                collection_names=collection_names,
                meta_topics=meta_topics
            )
            generated_at = stats_result.updated_at.isoformat() if stats_result.updated_at else datetime.utcnow().isoformat()

            return {
                "name": stats_result.name,
                "description": stats_result.description or "",
                "summary_text": summary_text,
                "total_collections": stats_result.total_collections,
                "total_documents": stats_result.total_documents,
                "total_chunks": stats_result.total_chunks,
                "key_topics": meta_topics,  # 後方互換性のためkey_topicsも残す
                "meta_topics": meta_topics,
                "meta_keywords": stats_result.meta_keywords or [],
                "collection_names": collection_names,
                "generated_at": generated_at
            }

        except Exception as e:
            logger.error(f"Error getting KB summary: {e}")
            raise
        finally:
            # 接続を確実にクローズ（接続リーク防止）
            db.close()

    def _generate_default_summary(
        self,
        name: str,
        description: str,
        total_collections: int,
        total_documents: int,
        total_chunks: int,
        collection_names: List[str],
        meta_topics: List[str] = None
    ) -> str:
        """デフォルトのサマリーテキストを生成"""

        summary_parts = [f"「{name}」ナレッジベースの概要です。"]

        if description:
            summary_parts.append(f"\n\n{description}")

        summary_parts.append(
            f"\n\n【統計情報】\n"
            f"- コレクション数: {total_collections}\n"
            f"- ドキュメント数: {total_documents}\n"
            f"- チャンク数: {total_chunks}"
        )

        # 含まれるコレクション（実際のコレクション名）
        if collection_names:
            summary_parts.append(
                f"\n\n【含まれるコレクション】\n"
                f"- " + "\n- ".join(collection_names[:10])  # 最大10件
            )
            if len(collection_names) > 10:
                summary_parts.append(f"\n...他 {len(collection_names) - 10} コレクション")

        # 主要トピック（LLM抽出）
        if meta_topics:
            summary_parts.append(
                f"\n\n【主要トピック】\n"
                f"- " + "\n- ".join(meta_topics[:10])  # 最大10件
            )

        return "".join(summary_parts)
