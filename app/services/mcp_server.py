"""MCP Server実装

MCPサーバーはapi-ragの9段階ハイブリッド検索パイプラインを使用して
ドキュメント検索を実行します。これによりfront-adminの検索表示と
同一のロジック（GraphRAG、BM25、Cross-Encoder等）が適用されます。
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import json
import httpx

from mcp.server import Server
from mcp import Tool
from mcp.types import TextContent

from app.services.kb_summary import KBSummaryService
from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseMCPServer:
    """ナレッジベース用MCPサーバー

    api-ragの9段階ハイブリッド検索パイプラインを使用します。
    """

    def __init__(self):
        self.server = Server("knowledge-base-tools")
        self.summary_service = KBSummaryService()
        self.rag_service_url = getattr(
            settings, 'rag_service_url', 'http://host.docker.internal:8010'
        )

        # ツール定義を保存
        self.tools_list = self._create_tools_list()

        # ツールを登録
        self._register_tools()

    def _create_tools_list(self) -> List[Tool]:
        """ツール定義一覧を作成"""
        return [
            Tool(
                name="search_documents",
                    description=(
                        "Search for specific information in the knowledge base using hybrid search. "
                        "This tool uses a 9-stage RAG pipeline including GraphRAG, BM25, and Cross-Encoder "
                        "for high-quality search results."
                        "\n\nUse this tool when the user asks about:"
                        "\n- Specific topics, people, companies, products, or services"
                        "\n- Technical details or procedures"
                        "\n- Product information and recommendations"
                        "\n- Concrete information (e.g., 'ADエスプラについて', '担当者は誰')"
                        "\n\nExamples:"
                        "\n- 'ADエスプラについて教えて'"
                        "\n- 'マイナビバイトの特徴は？'"
                        "\n- '採用課題を解決する商品は？'"
                        "\n\nDO NOT use this for:"
                        "\n- Questions about the knowledge base itself"
                        "\n- Requests for overall summaries or statistics"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "knowledge_base_id": {
                                "type": "string",
                                "description": "Knowledge base UUID",
                                "format": "uuid"
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Similarity threshold (0.0-1.0, lower is stricter)",
                                "default": 0.6,
                                "minimum": 0.0,
                                "maximum": 1.0
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["query", "knowledge_base_id"]
                    }
                ),
                Tool(
                    name="get_knowledge_base_summary",
                    description=(
                        "Get an overview and statistics of the entire knowledge base. "
                        "\n\nUse this tool ONLY when the user explicitly asks about:"
                        "\n- The knowledge base itself ('このナレッジベースについて')"
                        "\n- Overall structure ('全体の構成')"
                        "\n- Available information types ('どんな情報が含まれていますか')"
                        "\n- Statistics ('統計情報を見せて')"
                        "\n- Scope of the knowledge base ('すべての文書')"
                        "\n\nExamples:"
                        "\n- 'このナレッジベースについて教えて'"
                        "\n- '全体の構成は？'"
                        "\n- 'どんな情報が含まれていますか'"
                        "\n\nDO NOT use this for:"
                        "\n- Specific topic searches"
                        "\n- Questions about particular entities"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "knowledge_base_id": {
                                "type": "string",
                                "description": "Knowledge base UUID",
                                "format": "uuid"
                            }
                        },
                        "required": ["knowledge_base_id"]
                    }
                ),
                Tool(
                    name="normalize_ocr_text",
                    description=(
                        "Normalize OCR text by converting context-appropriate hyphens to Japanese long vowel marks. "
                        "\n\nThis tool uses LLM to intelligently detect katakana words with hyphens and convert them "
                        "to proper long vowel marks based on context."
                        "\n\nExamples:"
                        "\n- 'テレワ-ク勤務規程' → 'テレワーク勤務規程'"
                        "\n- 'マイナビ-広告' → 'マイナビー広告'"
                        "\n\nUse this tool for:"
                        "\n- OCR text preprocessing before indexing"
                        "\n- Batch normalization of existing documents"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "OCR text to normalize"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="find_related_products",
                    description=(
                        "Find products that can be combined or used together with a given product. "
                        "Uses GraphRAG to discover related products based on shared problems, targets, and features."
                        "\n\nUse this tool when the user asks about:"
                        "\n- Product combinations ('Xと組み合わせて使えるプランは？')"
                        "\n- Related products ('Xに関連する商品は？', 'Xと一緒に提案できるものは？')"
                        "\n- Complementary offerings ('Xで提案中ですが、ほかに有効なプランは？')"
                        "\n- Cross-selling opportunities"
                        "\n\nExamples:"
                        "\n- 'ADエスプラと組み合わせて提案できるプランは？'"
                        "\n- 'マイナビバイトで提案中ですが、ほかに有効なプランは？'"
                        "\n- 'WEB広告に関連する商品を教えて'"
                        "\n\nDO NOT use this for:"
                        "\n- Simple document searches"
                        "\n- Questions about specific product details (use search_documents instead)"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "The product name to find related products for"
                            },
                            "knowledge_base_id": {
                                "type": "string",
                                "description": "Knowledge base UUID (for tenant context)",
                                "format": "uuid"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of related products to return",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["product_name", "knowledge_base_id"]
                    }
                )
        ]

    def _register_tools(self):
        """ツールを登録"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """利用可能なツール一覧を返す"""
            return self.tools_list

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """ツールを実行"""
            try:
                logger.info(f"MCP Tool called: {name} with args: {arguments}")

                if name == "search_documents":
                    result = await self._search_documents(**arguments)
                elif name == "get_knowledge_base_summary":
                    result = await self._get_kb_summary(**arguments)
                elif name == "normalize_ocr_text":
                    result = await self._normalize_ocr_text(**arguments)
                elif name == "find_related_products":
                    result = await self._find_related_products(**arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'"
                    )]

                # 結果をJSON文字列として返す
                return [TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, indent=2)
                )]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _search_documents(
        self,
        query: str,
        knowledge_base_id: str,
        threshold: float = 0.6,
        max_results: int = 10,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """9段階ハイブリッド検索パイプラインでドキュメント検索を実行

        api-ragのHybridRetrieverを使用して以下の処理を行う：
        - Stage 0: GraphRAG前処理（エンティティ関係探索）
        - Stage 1: Atlas層フィルタリング
        - Stage 2-4: Sparse/Dense検索
        - Stage 5: RRFマージ + Graph Boost
        - Stage 6-7: BM25/Cross-Encoder Re-ranking
        - Stage 8: GraphRAGエンリッチメント

        Args:
            query: 検索クエリ
            knowledge_base_id: ナレッジベースID
            threshold: 類似度閾値（現在未使用、互換性のため維持）
            max_results: 最大結果数
            jwt_token: JWTトークン（内部API呼び出し用）
        """
        from sqlalchemy import text
        from app.core.database import get_db

        logger.info(f"[MCP] Hybrid search: query='{query[:50]}...', kb={knowledge_base_id}")

        try:
            # Get tenant_id from knowledge_base
            db = next(get_db())
            try:
                result = db.execute(
                    text("SELECT tenant_id FROM knowledge_bases WHERE id = :kb_id"),
                    {"kb_id": knowledge_base_id}
                )
                row = result.fetchone()
                tenant_id = str(row[0]) if row else None
            finally:
                db.close()

            if not tenant_id:
                return {
                    "query": query,
                    "knowledge_base_id": knowledge_base_id,
                    "error": f"Knowledge base {knowledge_base_id} not found",
                    "results": [],
                    "count": 0
                }

            # Call api-rag hybrid search endpoint
            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.rag_service_url}/api/rag/search/hybrid",
                    json={
                        "query": query,
                        "tenant_id": tenant_id,
                        "knowledge_base_id": knowledge_base_id,
                        "top_k": max_results,
                        "enable_graph": True,  # GraphRAG有効
                    },
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(
                        f"[MCP] api-rag hybrid search returned {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    return {
                        "query": query,
                        "knowledge_base_id": knowledge_base_id,
                        "error": f"Hybrid search failed: {response.status_code}",
                        "results": [],
                        "count": 0
                    }

                data = response.json()

            # Format results for LLM consumption
            formatted_results = []
            for item in data.get("results", []):
                # metadataにcollection_id, document_idを追加（トップレベルから）
                metadata = item.get("metadata", {})
                if item.get("collection_id"):
                    metadata["collection_id"] = item.get("collection_id")
                if item.get("document_id"):
                    metadata["document_id"] = item.get("document_id")
                if item.get("chunk_id"):
                    metadata["chunk_id"] = item.get("chunk_id")

                result_item = {
                    "content": item.get("content", ""),
                    "score": item.get("final_score", 0.0),
                    "metadata": metadata,
                    # 追加のスコア情報（デバッグ/分析用）
                    "scores": {
                        "rrf_score": item.get("rrf_score", 0.0),
                        "dense_score": item.get("dense_score", 0.0),
                        "sparse_score": item.get("sparse_score", 0.0),
                        "bm25_score": item.get("bm25_score", 0.0),
                        "cross_encoder_score": item.get("cross_encoder_score", 0.0),
                    }
                }
                # GraphRAGコンテキストがあれば追加
                if item.get("graph_context"):
                    result_item["graph_context"] = item["graph_context"]

                formatted_results.append(result_item)

            # メトリクス情報
            metrics = data.get("metrics", {})

            logger.info(
                f"[MCP] Hybrid search completed: {len(formatted_results)} results, "
                f"total_time={metrics.get('total_time_ms', 0):.1f}ms"
            )

            return {
                "query": query,
                "knowledge_base_id": knowledge_base_id,
                "results": formatted_results,
                "count": len(formatted_results),
                "metrics": {
                    "total_time_ms": metrics.get("total_time_ms", 0),
                    "stages": {
                        "graph_expansion": metrics.get("stage0_graph_time_ms", 0),
                        "atlas_filter": metrics.get("stage1_atlas_time_ms", 0),
                        "sparse_search": metrics.get("stage3_sparse_time_ms", 0),
                        "dense_search": metrics.get("stage4_dense_time_ms", 0),
                        "rrf_merge": metrics.get("stage5_rrf_time_ms", 0),
                        "bm25_rerank": metrics.get("stage6_bm25_time_ms", 0),
                        "cross_encoder": metrics.get("stage7_cross_encoder_time_ms", 0),
                    }
                },
                "graph_expansion": data.get("graph_expansion"),
            }

        except Exception as e:
            logger.error(f"[MCP] Hybrid search error: {e}", exc_info=True)
            return {
                "query": query,
                "knowledge_base_id": knowledge_base_id,
                "error": str(e),
                "results": [],
                "count": 0
            }

    async def _get_kb_summary(
        self,
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """ナレッジベースサマリーを取得"""

        kb_uuid = UUID(knowledge_base_id)

        summary = await self.summary_service.get_summary(kb_uuid)

        # summary_text に統計情報・コレクション名・主要トピックがすべて含まれているため、
        # 重複を避けるために statistics セクションは返さない
        return {
            "knowledge_base_id": knowledge_base_id,
            "summary": summary["summary_text"],
            "generated_at": summary["generated_at"]
        }

    async def _find_related_products(
        self,
        product_name: str,
        knowledge_base_id: str,
        limit: int = 10,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """GraphRAGを使用して関連商品を検索

        Args:
            product_name: 検索元の商品名
            knowledge_base_id: ナレッジベースID（テナントコンテキスト用）
            limit: 最大結果数
            jwt_token: JWTトークン（内部API呼び出し用）

        Returns:
            関連商品情報（source_product, related_products, recommendation_text）
        """
        from sqlalchemy import text
        from app.core.database import get_db

        logger.info(f"[MCP] Finding related products for: {product_name}")

        try:
            # Get tenant_id from knowledge_base
            db = next(get_db())
            try:
                result = db.execute(
                    text("SELECT tenant_id FROM knowledge_bases WHERE id = :kb_id"),
                    {"kb_id": knowledge_base_id}
                )
                row = result.fetchone()
                tenant_id = str(row[0]) if row else None
            finally:
                db.close()

            if not tenant_id:
                return {
                    "error": f"Knowledge base {knowledge_base_id} not found",
                    "source_product": None,
                    "related_products": [],
                    "recommendation_text": "ナレッジベースが見つかりませんでした。"
                }

            # Call api-rag /search/related-products endpoint
            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rag_service_url}/api/rag/search/related-products",
                    json={
                        "product_name": product_name,
                        "tenant_id": tenant_id,
                        "limit": limit,
                    },
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(f"[MCP] api-rag returned {response.status_code}: {response.text}")
                    return {
                        "error": f"Failed to call api-rag: {response.status_code}",
                        "source_product": None,
                        "related_products": [],
                        "recommendation_text": "関連商品の検索に失敗しました。"
                    }

                result = response.json()
                logger.info(
                    f"[MCP] Found {len(result.get('related_products', []))} related products "
                    f"for {product_name}"
                )

                return {
                    "product_name": product_name,
                    "knowledge_base_id": knowledge_base_id,
                    "source_product": result.get("source_product"),
                    "related_products": result.get("related_products", []),
                    "recommendation_text": result.get("recommendation_text", ""),
                    "count": len(result.get("related_products", []))
                }

        except Exception as e:
            logger.error(f"[MCP] find_related_products error: {e}", exc_info=True)
            return {
                "error": str(e),
                "source_product": None,
                "related_products": [],
                "recommendation_text": f"エラーが発生しました: {str(e)}"
            }

    async def _normalize_ocr_text(self, text: str) -> Dict[str, Any]:
        """OCR結果テキストをLLM経由で正規化

        カタカナ語の文脈でハイフン「-」を長音符「ー」に変換する。
        LLM（Ollama）を使用して文脈を考慮した正確な正規化を行う。

        Args:
            text: 正規化対象のOCRテキスト

        Returns:
            Dict[str, Any]: 正規化結果
        """
        try:
            # Ollama APIを使用してLLM正規化
            prompt = f"""以下のOCR結果テキストを正規化してください。

**正規化ルール**:
1. カタカナ語の後のハイフン「-」を長音符「ー」に変換
2. 文脈を考慮して適切に判断（例: 数式や欧文の「-」は変換しない）
3. 変換例:
   - 「テレワ-ク」→「テレワーク」
   - 「マイナビ-」→「マイナビー」
   - 「スキ-ム」→「スキーム」

**重要**: 正規化後のテキストのみを返してください。説明文は不要です。

---
対象テキスト:
{text}
---

正規化後のテキスト:"""

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": "pakachan/elyza-llama3-8b:latest",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # 低温度で安定した出力
                            "top_p": 0.9
                        }
                    }
                )
                response.raise_for_status()

                result = response.json()
                normalized_text = result.get("response", "").strip()

                # LLMが余計な説明を含む場合に備えて、最初の実質的なテキストのみ抽出
                if "\n" in normalized_text:
                    lines = [line.strip() for line in normalized_text.split("\n") if line.strip()]
                    # 説明文を除外（「正規化後」「以下は」などを含む行をスキップ）
                    for line in lines:
                        if not any(keyword in line for keyword in ["正規化後", "以下は", "対象テキスト", "---"]):
                            normalized_text = line
                            break

                logger.info(f"OCR normalization: '{text[:50]}...' → '{normalized_text[:50]}...'")

                return {
                    "original_text": text,
                    "normalized_text": normalized_text,
                    "status": "success"
                }

        except Exception as e:
            logger.error(f"Error normalizing OCR text: {e}")
            # エラー時は元のテキストを返す
            return {
                "original_text": text,
                "normalized_text": text,
                "status": "error",
                "error": str(e)
            }

    def get_tools(self) -> List[Tool]:
        """利用可能なツール一覧を返す"""
        return self.tools_list

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """ツールを実行

        Args:
            name: ツール名
            arguments: ツール引数
            jwt_token: JWTトークン（内部API呼び出し用）
        """
        try:
            logger.info(f"Executing tool: {name} with args: {arguments}")

            if name == "search_documents":
                result = await self._search_documents(**arguments, jwt_token=jwt_token)
            elif name == "get_knowledge_base_summary":
                result = await self._get_kb_summary(**arguments)
            elif name == "normalize_ocr_text":
                result = await self._normalize_ocr_text(**arguments)
            elif name == "find_related_products":
                result = await self._find_related_products(**arguments, jwt_token=jwt_token)
            else:
                raise ValueError(f"Unknown tool: {name}")

            return result

        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            raise

    def get_server(self) -> Server:
        """MCPサーバーインスタンスを返す"""
        return self.server


# グローバルインスタンス
_mcp_server_instance: Optional[KnowledgeBaseMCPServer] = None


def get_mcp_server() -> KnowledgeBaseMCPServer:
    """MCPサーバーのシングルトンインスタンスを取得"""
    global _mcp_server_instance
    if _mcp_server_instance is None:
        _mcp_server_instance = KnowledgeBaseMCPServer()
    return _mcp_server_instance
