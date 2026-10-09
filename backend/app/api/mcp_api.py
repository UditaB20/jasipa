from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
from app.database.session import get_db
from app.mcp.server import MCPServer
from app.auth.security import require_hr

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP) ATS Connector"])

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

@router.get("/tools")
def list_mcp_tools(current_user: dict = Depends(require_hr)):
    """
    Returns JSON Schema of all MCP ATS tools exposed by the JASIPA server.
    """
    return {
        "protocolVersion": "2024-11-05",
        "tools": MCPServer.list_tools()
    }

@router.post("/execute")
def execute_mcp_tool(
    req: ToolCallRequest, 
    current_user: dict = Depends(require_hr), 
    db: Session = Depends(get_db)
):
    """
    Directly invokes an ATS MCP tool with structured arguments.
    """
    try:
        result = MCPServer.execute_tool(db, req.name, req.arguments)
        return {
            "isError": False,
            "content": [{"type": "text", "text": str(result)}],
            "result": result
        }
    except Exception as e:
        return {
            "isError": True,
            "content": [{"type": "text", "text": str(e)}],
            "error": str(e)
        }
