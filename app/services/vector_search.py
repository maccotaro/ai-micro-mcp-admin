"""ベクトル検索サービス - エンタープライズRAG Phase 2統合版

このサービスはai-micro-api-adminのHybrid Search APIを呼び出して、
7段階RAGパイプラインを活用した高精度な検索を提供します。

7段階パイプライン:
- Stage 1: Atlas層フィルタリング（KB/Collection）
- Stage 2: メタデータフィルタ構築
- Stage 3: スパース検索（500件）
- Stage 4: Dense検索（500件）
- Stage 5: RRF（Reciprocal Rank Fusion）マージ
- Stage 6: BM25 Re-ranker（600→100件）
- Stage 7: Cross-Encoder Re-ranker（100→10件）
"""
import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """ベクトル検索サービス（Hybrid Search API統合版）"""

    def __init__(self):
        # api-adminのベースURL（設定から取得）
        self.api_admin_url = getattr(
            settings,
            "api_admin_url",
            "http://host.docker.internal:8003"
        )
        self.hybrid_search_endpoint = f"{self.api_admin_url}/admin/search/hybrid"

        # HTTPクライアント設定
        self.client = httpx.AsyncClient(
            timeout=120.0,  # 2分タイムアウト（Cross-Encoder re-rankingに時間がかかるため）
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def search(
        self,
        query: str,
        knowledge_base_id: UUID,
        threshold: float = 0.6,
        top_k: int = 10,
        user_context: Optional[Dict[str, Any]] = None,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ベクトル検索を実行（Hybrid Search API経由）

        Args:
            query: 検索クエリ
            knowledge_base_id: ナレッジベースID
            threshold: 類似度閾値（現在は未使用、APIが内部で処理）
            top_k: 返却結果数
            user_context: ユーザーコンテキスト（tenant_id, department, clearance_level）
            jwt_token: JWTトークン（API認証用）

        Returns:
            List[Dict]: 検索結果リスト
        """
        try:
            logger.info(
                f"Vector search: query='{query}', "
                f"kb_id={knowledge_base_id}, "
                f"threshold={threshold}, top_k={top_k}"
            )

            # knowledge_base_idからtenant_idを取得
            tenant_id = await self._get_tenant_id_from_kb(knowledge_base_id)

            if not tenant_id:
                logger.warning(
                    f"Could not find tenant_id for kb_id={knowledge_base_id}, "
                    f"using default tenant"
                )
                # デフォルトテナントID
                tenant_id = UUID("00000000-0000-0000-0000-000000000000")

            # user_filtersの構築
            user_filters = {}
            if user_context:
                if "department" in user_context:
                    user_filters["department"] = user_context["department"]
                if "clearance_level" in user_context:
                    user_filters["clearance_level"] = user_context["clearance_level"]

            # Hybrid Search APIリクエスト
            request_body = {
                "query": query,
                "tenant_id": str(tenant_id),
                "knowledge_base_id": str(knowledge_base_id),
                "user_filters": user_filters if user_filters else None,
                "top_k": top_k
            }

            logger.debug(f"Calling Hybrid Search API: {request_body}")

            # ヘッダー構築
            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
                logger.debug("JWT token added to Authorization header")

            # API呼び出し（非同期処理）
            response = await self.client.post(
                self.hybrid_search_endpoint,
                json=request_body,
                headers=headers
            )

            # エラーハンドリング
            if response.status_code != 200:
                logger.error(
                    f"Hybrid Search API error: status={response.status_code}, "
                    f"response={response.text}"
                )
                return []

            result_data = response.json()

            # レスポンス形式の変換
            results = []
            for item in result_data.get("results", []):
                results.append({
                    "content": item["content"],
                    "score": item["final_score"],  # Cross-Encoderスコアを使用
                    "metadata": {
                        "chunk_id": item["chunk_id"],
                        "document_id": item["document_id"],
                        "chunk_index": item["chunk_index"],
                        "collection_id": item.get("collection_id"),
                        "knowledge_base_id": str(knowledge_base_id),
                        # スコア詳細
                        "sparse_score": item.get("sparse_score", 0.0),
                        "dense_score": item.get("dense_score", 0.0),
                        "rrf_score": item.get("rrf_score", 0.0),
                        "bm25_score": item.get("bm25_score", 0.0),
                        "hybrid_score": item.get("hybrid_score", 0.0),
                        "cross_encoder_score": item.get("cross_encoder_score", 0.0),
                        **item.get("metadata", {})
                    }
                })

            # メトリクスのログ記録
            metrics = result_data.get("metrics", {})
            logger.info(
                f"Hybrid search completed: {len(results)} results, "
                f"total_time={metrics.get('total_time_ms', 0):.2f}ms, "
                f"atlas_kbs={metrics.get('atlas_matched_kbs', 0)}, "
                f"sparse={metrics.get('sparse_count', 0)}, "
                f"dense={metrics.get('dense_count', 0)}, "
                f"merged={metrics.get('merged_count', 0)}"
            )

            return results

        except httpx.RequestError as e:
            logger.error(f"HTTP request error to Hybrid Search API: {e}")
            return []
        except Exception as e:
            logger.error(f"Vector search error: {e}", exc_info=True)
            return []

    async def _get_tenant_id_from_kb(self, knowledge_base_id: UUID) -> Optional[UUID]:
        """knowledge_base_idからtenant_idを取得

        Args:
            knowledge_base_id: ナレッジベースID

        Returns:
            Optional[UUID]: テナントID（見つからない場合はNone）
        """
        try:
            # データベース接続取得
            db_gen = get_db()
            db = next(db_gen)

            try:
                # knowledge_basesテーブルからtenant_idを取得
                from sqlalchemy import text
                result = db.execute(
                    text("SELECT tenant_id FROM knowledge_bases WHERE id = :kb_id"),
                    {"kb_id": str(knowledge_base_id)}
                )
                row = result.fetchone()

                if row and row[0]:
                    return UUID(row[0]) if isinstance(row[0], str) else row[0]

                return None

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error fetching tenant_id for kb_id={knowledge_base_id}: {e}")
            return None

    async def close(self):
        """HTTPクライアントをクローズ"""
        await self.client.aclose()

    def __del__(self):
        """デストラクタでクライアントをクローズ"""
        try:
            asyncio.get_event_loop().run_until_complete(self.close())
        except Exception:
            pass
