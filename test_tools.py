#!/usr/bin/env python3
"""Test de la logica de cada tool con la API de Gmail simulada (sin red ni credenciales)."""

import asyncio
import base64
import json
import sys

import server


class FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class FakeMessages:
    def list(self, **kw):
        self._last = kw
        return FakeRequest({"messages": [{"id": "m1", "threadId": "t1"}]})

    def get(self, **kw):
        if kw.get("format") == "metadata":
            return FakeRequest(
                {
                    "id": kw["id"],
                    "threadId": "t1",
                    "snippet": "hola mundo",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "ana@example.com"},
                            {"name": "Subject", "value": "Ping"},
                            {"name": "Date", "value": "Mon, 1 Jan 2026"},
                        ]
                    },
                }
            )
        body = base64.urlsafe_b64encode(b"cuerpo real del mail").decode()
        return FakeRequest(
            {
                "id": kw["id"],
                "threadId": "t1",
                "labelIds": ["INBOX", "UNREAD"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "ana@example.com"},
                        {"name": "To", "value": "yo@example.com"},
                        {"name": "Subject", "value": "Ping"},
                    ],
                    "body": {"data": body},
                    "parts": [],
                },
            }
        )

    def send(self, **kw):
        raw = kw["body"]["raw"]
        decoded = base64.urlsafe_b64decode(raw).decode()
        assert "To: bob@example.com" in decoded, decoded
        assert "Asunto de prueba" in decoded
        return FakeRequest({"id": "sent1", "threadId": "t9"})

    def modify(self, **kw):
        return FakeRequest({"id": kw["id"], "labelIds": ["STARRED"]})

    def trash(self, **kw):
        return FakeRequest({"id": kw["id"]})


class FakeLabels:
    def list(self, **kw):
        return FakeRequest({"labels": [{"id": "INBOX", "name": "INBOX", "type": "system"}]})


class FakeUsers:
    def messages(self):
        return FakeMessages()

    def labels(self):
        return FakeLabels()


class FakeService:
    def users(self):
        return FakeUsers()


async def call(name, args):
    res = await server.mcp.call_tool(name, args)
    payload = json.loads(res.content[0].text)
    return payload


async def main() -> int:
    server.gmail = lambda: FakeService()

    got = await call("list_messages", {"query": "is:unread", "max_results": 5})
    assert got["count"] == 1 and got["messages"][0]["subject"] == "Ping", got
    assert got["messages"][0]["from"] == "ana@example.com", got
    print("[ok] list_messages ->", got["messages"][0])

    got = await call("get_message", {"message_id": "m1"})
    assert got["body"] == "cuerpo real del mail", got
    assert got["labels"] == ["INBOX", "UNREAD"], got
    print("[ok] get_message -> body y labels correctos")

    got = await call("send_message", {"to": "bob@example.com", "subject": "Asunto de prueba", "body": "hey"})
    assert got["status"] == "sent" and got["id"] == "sent1", got
    print("[ok] send_message ->", got)

    got = await call("list_labels", {})
    assert got["labels"][0]["name"] == "INBOX", got
    print("[ok] list_labels ->", got["labels"])

    got = await call("modify_labels", {"message_id": "m1", "add": "STARRED", "remove": "UNREAD"})
    assert got["labels"] == ["STARRED"], got
    print("[ok] modify_labels ->", got)

    got = await call("trash_message", {"message_id": "m1"})
    assert got["status"] == "trashed", got
    print("[ok] trash_message ->", got)

    print("\n[OK] Todas las tools pasan con la API simulada.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
