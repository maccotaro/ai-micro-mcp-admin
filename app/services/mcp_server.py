"""MCP Server実装"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from mcp.server import Server
from mcp import Tool
from mcp.types import TextContent

from app.services.vector_search import VectorSearchService
from app.services.kb_summary import KBSummaryService

logger = logging.getLogger(__name__)


class KnowledgeBaseMCPServer:
    """ナレッジベース用MCPサーバー"""

    def __init__(self):
        self.server = Server("knowledge-base-tools")
        self.vector_service = VectorSearchService()
        self.summary_service = KBSummaryService()

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
                        "Search for specific information in the knowledge base documents. "
                        "\n\nUse this tool when the user asks about:"
                        "\n- Specific topics, people, companies, products, or services"
                        "\n- Technical details or procedures"
                        "\n- Concrete information (e.g., 'エーループについて', '担当者は誰')"
                        "\n\nExamples:"
                        "\n- 'エーループについて教えて'"
                        "\n- 'ABC会社のサービスは？'"
                        "\n- 'ハラスメント相談窓口は誰ですか？'"
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
        """ドキュメント検索を実行

        Args:
            query: 検索クエリ
            knowledge_base_id: ナレッジベースID
            threshold: 類似度閾値
            max_results: 最大結果数
            jwt_token: JWTトークン（内部API呼び出し用）
        """

        kb_uuid = UUID(knowledge_base_id)

        results = await self.vector_service.search(
            query=query,
            knowledge_base_id=kb_uuid,
            threshold=threshold,
            top_k=max_results,
            jwt_token=jwt_token
        )

        return {
            "query": query,
            "knowledge_base_id": knowledge_base_id,
            "threshold": threshold,
            "results": [
                {
                    "content": doc["content"],
                    "score": doc["score"],
                    "metadata": doc["metadata"]
                }
                for doc in results
            ],
            "count": len(results)
        }

    async def _get_kb_summary(
        self,
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """ナレッジベースサマリーを取得"""

        kb_uuid = UUID(knowledge_base_id)

        summary = await self.summary_service.get_summary(kb_uuid)

        return {
            "knowledge_base_id": knowledge_base_id,
            "summary": summary["summary_text"],
            "statistics": {
                "total_documents": summary["total_documents"],
                "total_collections": summary["total_collections"],
                "total_chunks": summary["total_chunks"],
                "key_topics": summary["key_topics"]
            },
            "generated_at": summary["generated_at"]
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
            import httpx
            from app.core.config import settings

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
