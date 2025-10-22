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
        max_results: int = 10
    ) -> Dict[str, Any]:
        """ドキュメント検索を実行"""

        kb_uuid = UUID(knowledge_base_id)

        results = await self.vector_service.search(
            query=query,
            knowledge_base_id=kb_uuid,
            threshold=threshold,
            top_k=max_results
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

    def get_tools(self) -> List[Tool]:
        """利用可能なツール一覧を返す"""
        return self.tools_list

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを実行"""
        try:
            logger.info(f"Executing tool: {name} with args: {arguments}")

            if name == "search_documents":
                result = await self._search_documents(**arguments)
            elif name == "get_knowledge_base_summary":
                result = await self._get_kb_summary(**arguments)
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
