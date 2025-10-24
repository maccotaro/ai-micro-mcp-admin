"""ベクトル検索サービス"""
import asyncio
import logging
from typing import List, Dict, Any
from uuid import UUID

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import PGVector

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """ベクトル検索サービス"""

    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model
        )

        self.vector_store = PGVector(
            collection_name=settings.collection_name,
            connection_string=settings.database_url,
            embedding_function=self.embeddings,
            distance_strategy="cosine"
        )

    async def search(
        self,
        query: str,
        knowledge_base_id: UUID,
        threshold: float = 0.6,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """ベクトル検索を実行（非同期対応）"""

        try:
            logger.info(
                f"Vector search: query='{query}', "
                f"kb_id={knowledge_base_id}, "
                f"threshold={threshold}, top_k={top_k}"
            )

            # LangChain PGVectorのfilter機能に問題があるため、
            # filterなしで検索してから手動でフィルタリング
            # より多くの結果を取得してから絞り込む
            search_k = top_k * 10  # 10倍の結果を取得

            # 同期ブロッキング処理を別スレッドで実行（並行処理対応）
            results = await asyncio.to_thread(
                self.vector_store.similarity_search_with_score,
                query,
                k=search_k
            )

            # knowledge_base_idと閾値でフィルタリング
            filtered_results = []
            for doc, score in results:
                # メタデータでKB IDをチェック
                if doc.metadata.get("knowledge_base_id") == str(knowledge_base_id):
                    # LangChainのPGVectorは類似度（高い=類似）を返すため、
                    # 距離に変換してから閾値と比較
                    distance = 1.0 - score
                    logger.debug(f"KB ID match, Similarity: {score:.4f}, Distance: {distance:.4f}, Threshold: {threshold}")

                    if distance <= threshold:
                        filtered_results.append({
                            "content": doc.page_content,
                            "score": float(score),
                            "metadata": doc.metadata
                        })
                        # 必要な数だけ取得したら終了
                        if len(filtered_results) >= top_k:
                            break

            logger.info(f"Found {len(filtered_results)} results")
            return filtered_results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
