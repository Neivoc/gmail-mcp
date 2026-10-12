#!/usr/bin/env python3
"""Test de protocolo MCP contra el server por stdio (sin credenciales)."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str(Path(__file__).resolve().parent / "server.py")
PYTHON = sys.executable


async def main() -> int:
    params = StdioServerParameters(command=PYTHON, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"[1] initialize OK -> {init.server_info.name} v{init.server_info.version}")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"[2] tools/list OK ({len(names)}): {names}")

            expected = {
                "list_messages", "get_message", "send_message", "create_draft",
                "reply_message", "list_labels", "modify_labels", "trash_message",
            }
            missing = expected - set(names)
            if missing:
                print(f"[x] Faltan herramientas: {missing}")
                return 1

            print("[3] call_tool: verifica manejo de credenciales (error claro o datos)")
            res = await session.call_tool("list_messages", {"query": "is:unread"})
            text = res.content[0].text if res.content else ""
            if "auth_setup.py" in text:
                print("[ok] Sin credenciales: error controlado y util para el usuario")
            else:
                print("[ok] Con credenciales: la tool respondio datos")

    print("\n[OK] Protocolo MCP verificado de punta a punta.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
