"""コレクションサマリーサービス"""
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import text
from app.core.database import get_db

logger = logging.getLogger(__name__)


class CollectionSummaryService:
    """コレクションサマリーサービス"""

    async def get_summary(self, collection_id: UUID) -> Dict[str, Any]:
        """コレクションのサマリーを取得

        description を単一ソースとして使用。
        meta_topics, meta_keywords があれば検索参考情報として付加。
        """

        db = next(get_db())
        try:
            # Collection基本情報と統計を取得（description, meta_topics, meta_keywords 含む）
            stats_query = text("""
                SELECT
                    c.name,
                    c.description,
                    c.meta_topics,
                    c.meta_keywords,
                    c.meta_statistics,
                    c.updated_at,
                    kb.id as knowledge_base_id,
                    kb.name as knowledge_base_name,
                    COUNT(DISTINCT d.id) as total_documents,
                    COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM collections c
                JOIN knowledge_bases kb ON kb.id = c.knowledge_base_id
                LEFT JOIN documents d ON d.collection_id = c.id
                WHERE c.id = :collection_id
                GROUP BY c.id, c.name, c.description, c.meta_topics, c.meta_keywords,
                         c.meta_statistics, c.updated_at, kb.id, kb.name
            """)

            stats_result = db.execute(
                stats_query,
                {"collection_id": str(collection_id)}
            ).fetchone()

            if not stats_result:
                raise ValueError(f"Collection {collection_id} not found")

            # ドキュメント名を取得
            docs_query = text("""
                SELECT original_filename FROM documents
                WHERE collection_id = :collection_id
                ORDER BY created_at DESC
                LIMIT 20
            """)

            docs_result = db.execute(
                docs_query,
                {"collection_id": str(collection_id)}
            ).fetchall()

            document_names = [row[0] for row in docs_result if row[0]] if docs_result else []

            # meta_topics: LLM抽出の主要トピック
            meta_topics = []
            if stats_result.meta_topics:
                meta_topics = stats_result.meta_topics if isinstance(stats_result.meta_topics, list) else list(stats_result.meta_topics)

            # meta_keywords: LLM抽出のキーワード
            meta_keywords = []
            if stats_result.meta_keywords:
                meta_keywords = stats_result.meta_keywords if isinstance(stats_result.meta_keywords, list) else list(stats_result.meta_keywords)

            # サマリーテキストを生成
            summary_text = self._generate_default_summary(
                name=stats_result.name,
                description=stats_result.description,
                knowledge_base_name=stats_result.knowledge_base_name,
                total_documents=stats_result.total_documents,
                total_chunks=stats_result.total_chunks,
                document_names=document_names,
                meta_topics=meta_topics
            )
            generated_at = stats_result.updated_at.isoformat() if stats_result.updated_at else datetime.utcnow().isoformat()

            return {
                "name": stats_result.name,
                "description": stats_result.description or "",
                "summary_text": summary_text,
                "knowledge_base_id": str(stats_result.knowledge_base_id),
                "knowledge_base_name": stats_result.knowledge_base_name,
                "total_documents": stats_result.total_documents,
                "total_chunks": stats_result.total_chunks,
                "meta_topics": meta_topics,
                "meta_keywords": meta_keywords,
                "document_names": document_names,
                "generated_at": generated_at
            }

        except Exception as e:
            logger.error(f"Error getting Collection summary: {e}")
            raise
        finally:
            # 接続を確実にクローズ（接続リーク防止）
            db.close()

    async def get_summaries_by_kb(self, knowledge_base_id: UUID) -> List[Dict[str, Any]]:
        """ナレッジベース内の全コレクションのサマリーを取得"""

        db = next(get_db())
        try:
            query = text("""
                SELECT
                    c.id,
                    c.name,
                    c.description,
                    c.meta_topics,
                    c.meta_keywords,
                    c.updated_at,
                    COUNT(DISTINCT d.id) as total_documents,
                    COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM collections c
                LEFT JOIN documents d ON d.collection_id = c.id
                WHERE c.knowledge_base_id = :kb_id
                GROUP BY c.id, c.name, c.description, c.meta_topics, c.meta_keywords, c.updated_at
                ORDER BY c.created_at DESC
            """)

            result = db.execute(
                query,
                {"kb_id": str(knowledge_base_id)}
            ).fetchall()

            collections = []
            for row in result:
                meta_topics = row.meta_topics if isinstance(row.meta_topics, list) else (list(row.meta_topics) if row.meta_topics else [])
                meta_keywords = row.meta_keywords if isinstance(row.meta_keywords, list) else (list(row.meta_keywords) if row.meta_keywords else [])

                collections.append({
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description or "",
                    "total_documents": row.total_documents,
                    "total_chunks": row.total_chunks,
                    "meta_topics": meta_topics,
                    "meta_keywords": meta_keywords,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                })

            return collections

        except Exception as e:
            logger.error(f"Error getting Collection summaries for KB {knowledge_base_id}: {e}")
            raise
        finally:
            db.close()

    def _generate_default_summary(
        self,
        name: str,
        description: str,
        knowledge_base_name: str,
        total_documents: int,
        total_chunks: int,
        document_names: List[str],
        meta_topics: List[str] = None
    ) -> str:
        """デフォルトのサマリーテキストを生成"""

        summary_parts = [f"「{name}」コレクションの概要です。"]
        summary_parts.append(f"（ナレッジベース: {knowledge_base_name}）")

        if description:
            summary_parts.append(f"\n\n{description}")

        summary_parts.append(
            f"\n\n【統計情報】\n"
            f"- ドキュメント数: {total_documents}\n"
            f"- チャンク数: {total_chunks}"
        )

        # 含まれるドキュメント
        if document_names:
            summary_parts.append(
                f"\n\n【含まれるドキュメント】\n"
                f"- " + "\n- ".join(document_names[:10])  # 最大10件
            )
            if len(document_names) > 10:
                summary_parts.append(f"\n...他 {len(document_names) - 10} ドキュメント")

        # 主要トピック（LLM抽出）
        if meta_topics:
            summary_parts.append(
                f"\n\n【主要トピック】\n"
                f"- " + "\n- ".join(meta_topics[:10])  # 最大10件
            )

        return "".join(summary_parts)
