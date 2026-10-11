"""Model Context Protocol server (stdio transport) for the JASIPA ATS tools.

Implements the JSON-RPC subset of MCP that tool clients use: ``initialize``, ``tools/list`` and
``tools/call`` (plus ``ping`` and notifications). It exposes the same tools as /api/mcp. Recording a
human hiring decision is deliberately not available through MCP, and panel recommendations written
through it are restricted to human-review routing labels.

Run from the backend directory:
    python -m app.mcp.stdio_server

Example client configuration:
    {"command": "/path/to/backend/.venv/bin/python", "args": ["-m", "app.mcp.stdio_server"], "cwd": "/path/to/backend"}
"""
import json
import sys
from typing import Any, Dict, Optional

from app.database.session import SessionLocal
from app.mcp.server import MCPServer

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "jasipa-ats", "version": "1.1.0"}


def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None  # Notification (e.g. notifications/initialized): no response.
    if method == "initialize":
        return _result(request_id, {"protocolVersion": PROTOCOL_VERSION, "serverInfo": SERVER_INFO,
                                    "capabilities": {"tools": {"listChanged": False}}})
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": MCPServer.list_tools()})
    if method == "tools/call":
        params = message.get("params") or {}
        db = SessionLocal()
        try:
            output = MCPServer.execute_tool(db, params.get("name", ""), params.get("arguments") or {})
            return _result(request_id, {"content": [{"type": "text", "text": json.dumps(output, default=str)}], "isError": False})
        except Exception as exc:  # Tool errors are reported to the client, not raised.
            db.rollback()
            return _result(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
        finally:
            db.close()
    return _error(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
        else:
            response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
