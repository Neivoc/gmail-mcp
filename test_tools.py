#!/usr/bin/env python3
"""Test de la logica de cada tool con la API de Gmail simulada (sin red ni credenciales)."""

import asyncio
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import server  # noqa: E402

ME = "yo@example.com"
CAPTURED: list[str] = []


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


class FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class FakeBatch:
    def __init__(self):
        self._reqs = []

    def add(self, request, callback=None, request_id=None):
        self._reqs.append((request, callback, request_id))
        return request_id

    def execute(self):
        for request, callback, rid in self._reqs:
            if callback:
                callback(rid, request.execute(), None)


class FakeMessages:
    def list(self, **kw):
        return FakeRequest({"messages": [{"id": "m1", "threadId": "t1"}]})

    def _metadata(self, mid):
        headers = {"From": "ana@example.com", "To": ME, "Subject": "Ping",
                   "Message-ID": "<orig-1@mail>", "References": ""}
        if mid == "m2":  # mensaje propio: From == yo
            headers.update({"From": ME, "To": "team@example.com"})
        if mid == "m3":  # con Reply-To
            headers.update({"Reply-To": "lista@example.com"})
        return FakeRequest(
            {
                "id": mid,
                "threadId": "t1",
                "snippet": "hola mundo",
                "payload": {"headers": [{"name": k, "value": v} for k, v in headers.items()]
                            + [{"name": "Date", "value": "Mon, 1 Jan 2026"}]},
            }
        )

    def get(self, **kw):
        if kw.get("format") == "metadata":
            return self._metadata(kw["id"])
        payload = {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "ana@example.com"},
                {"name": "To", "value": ME},
                {"name": "Subject", "value": "Ping"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": b64("cuerpo real del mail")}},
                {"mimeType": "text/html", "body": {"data": b64("<p>cuerpo</p>")}},
                {"mimeType": "application/pdf", "filename": "doc.pdf",
                 "body": {"attachmentId": "att1", "size": 123}},
            ],
        }
        return FakeRequest({"id": kw["id"], "threadId": "t1",
                            "labelIds": ["INBOX", "UNREAD"], "payload": payload})

    def send(self, **kw):
        CAPTURED.append(base64.urlsafe_b64decode(kw["body"]["raw"]).decode())
        return FakeRequest({"id": "sent1", "threadId": kw["body"].get("threadId", "t9")})

    def modify(self, **kw):
        return FakeRequest({"id": kw["id"], "labelIds": ["STARRED"]})

    def trash(self, **kw):
        return FakeRequest({"id": kw["id"]})


class FakeDrafts:
    def create(self, **kw):
        CAPTURED.append(base64.urlsafe_b64decode(kw["body"]["message"]["raw"]).decode())
        return FakeRequest({"id": "d1", "message": {"id": "dm1"}})


class FakeLabels:
    def list(self, **kw):
        return FakeRequest({"labels": [{"id": "INBOX", "name": "INBOX", "type": "system"}]})


class FakeUsers:
    def messages(self):
        return FakeMessages()

    def labels(self):
        return FakeLabels()

    def drafts(self):
        return FakeDrafts()

    def getProfile(self, **kw):
        return FakeRequest({"emailAddress": ME})


class FakeService:
    def users(self):
        return FakeUsers()

    def new_batch_http_request(self):
        return FakeBatch()


async def call(name, args):
    res = await server.mcp.call_tool(name, args)
    return json.loads(res.content[0].text)


async def main() -> int:
    server.gmail = lambda: FakeService()

    got = await call("list_messages", {"query": "is:unread", "max_results": 5})
    assert got["count"] == 1 and got["messages"][0]["subject"] == "Ping", got
    assert got["messages"][0]["from"] == "ana@example.com", got
    print("[ok] list_messages (batch) ->", got["messages"][0]["subject"])

    got = await call("get_message", {"message_id": "m1"})
    assert got["body"] == "cuerpo real del mail", got
    assert got["body_html"] == "<p>cuerpo</p>", got
    assert got["attachments"][0]["filename"] == "doc.pdf", got
    assert got["untrusted_content"] is True
    print("[ok] get_message -> texto, html y adjuntos OK")

    got = await call("send_message", {"to": "bob@example.com", "subject": "Asunto de prueba", "body": "hey"})
    assert got["status"] == "sent" and "To: bob@example.com" in CAPTURED[-1], got
    print("[ok] send_message ->", got)

    got = await call("create_draft", {"to": "bob@example.com", "subject": "Borrador", "body": "hola"})
    assert got["status"] == "draft" and got["draft_id"] == "d1", got
    print("[ok] create_draft ->", got)

    got = await call("reply_message", {"message_id": "m1", "body": "recibido"})
    assert got["status"] == "replied", got
    assert "To: ana@example.com" in CAPTURED[-1], CAPTURED[-1]
    assert "In-Reply-To: <orig-1@mail>" in CAPTURED[-1], CAPTURED[-1]
    print("[ok] reply_message -> responde al remitente con cabeceras")

    await call("reply_message", {"message_id": "m2", "body": "x"})
    assert "To: team@example.com" in CAPTURED[-1], CAPTURED[-1]
    print("[ok] reply_message -> no se responde a si mismo (usa To original)")

    await call("reply_message", {"message_id": "m3", "body": "x"})
    assert "To: lista@example.com" in CAPTURED[-1], CAPTURED[-1]
    print("[ok] reply_message -> respeta Reply-To")

    got = await call("list_labels", {})
    assert got["labels"][0]["name"] == "INBOX", got
    print("[ok] list_labels ->", got["labels"][0]["name"])

    got = await call("modify_labels", {"message_id": "m1", "add": "STARRED", "remove": "UNREAD"})
    assert got["labels"] == ["STARRED"], got
    print("[ok] modify_labels ->", got["labels"])

    got = await call("trash_message", {"message_id": "m1"})
    assert got["status"] == "trashed", got
    print("[ok] trash_message ->", got["status"])

    # Allowlist de destinatarios -------------------------------------------
    server.ALLOWED_RECIPIENTS = frozenset({"bob@example.com"})
    got = await call("send_message", {"to": "Bob <bob@example.com>", "subject": "s", "body": "b"})
    assert got["status"] == "sent", got
    print("[ok] allowlist -> permite destinatario en la lista")

    try:
        await server.mcp.call_tool("send_message", {"to": "mallory@evil.com", "subject": "s", "body": "b"})
        raise AssertionError("deberia bloquear destinatario fuera de la allowlist")
    except AssertionError:
        raise
    except Exception as exc:  # ToolError
        assert "allowlist" in str(exc).lower(), exc
    print("[ok] allowlist -> bloquea destinatario fuera de la lista")
    server.ALLOWED_RECIPIENTS = frozenset()

    # Destinatario vacio ----------------------------------------------------
    try:
        await server.mcp.call_tool("send_message", {"to": "   ", "subject": "s", "body": "b"})
        raise AssertionError("deberia rechazar 'to' vacio")
    except AssertionError:
        raise
    except Exception as exc:  # ToolError
        assert "vacio" in str(exc).lower() or "destinatario" in str(exc).lower(), exc
    print("[ok] send_message -> rechaza 'to' vacio")

    server.SEND_ENABLED = False
    try:
        await server.mcp.call_tool("send_message", {"to": "x@y.com", "subject": "s", "body": "b"})
        raise AssertionError("el envio deberia estar bloqueado")
    except AssertionError:
        raise
    except Exception as exc:  # ToolError
        assert "desactivado" in str(exc), exc
    print("[ok] GMAIL_MCP_ALLOW_SEND=0 -> send_message bloqueado")
    server.SEND_ENABLED = True

    print("\n[OK] Todas las tools pasan con la API simulada.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
