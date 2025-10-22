"""MCPエンドポイント"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Dict, Any
import logging

from app.services.mcp_server import get_mcp_server
from app.dependencies.auth import get_current_user
from app.core.permissions import require_knowledge_base_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/tools")
async def list_tools(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """利用可能なツール一覧（認証必須）"""

    logger.info(f"User {current_user.get('sub')} listing MCP tools")

    mcp_server = get_mcp_server()
    tools = mcp_server.get_tools()

    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in tools
        ]
    }


@router.post("/call_tool")
async def call_tool(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """MCPツールを呼び出し（認証必須）"""

    tool_name = request.get("name")
    arguments = request.get("arguments", {})

    logger.info(
        f"User {current_user.get('sub')} calling tool: {tool_name} "
        f"with args: {arguments}"
    )

    # knowledge_base_idの権限チェック
    kb_id_str = arguments.get("knowledge_base_id")
    if kb_id_str:
        try:
            kb_id = UUID(kb_id_str)
            await require_knowledge_base_access(current_user, kb_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid knowledge_base_id format"
            )

    # MCPツール実行
    mcp_server = get_mcp_server()
    result = await mcp_server.execute_tool(tool_name, arguments)

    return {
        "result": result
    }
