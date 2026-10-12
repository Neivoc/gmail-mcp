#!/usr/bin/env python3
"""Servidor MCP local para Gmail (transporte stdio).

Arranca con:  python server.py
Antes ejecuta: python auth_setup.py  (genera credentials/token.json)
"""

from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

BASE_DIR = Path(__file__).resolve().parent
CRED_DIR = BASE_DIR / "credentials"
CLIENT_SECRET_FILE = CRED_DIR / "gcp-oauth.keys.json"
TOKEN_FILE = CRED_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

mcp = MCPServer("gmail")


def _load_creds() -> Credentials:
    if not TOKEN_FILE.exists():
        raise ToolError(
            f"No existe {TOKEN_FILE}. Ejecuta primero: python auth_setup.py"
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise ToolError(
                "Credenciales invalidas. Vuelve a ejecutar auth_setup.py"
            )
    return creds


def gmail():
    return build("gmail", "v1", credentials=_load_creds(), cache_discovery=False)


def _headers(payload: dict) -> dict[str, str]:
    return {
        h.get("name", "").lower(): h.get("value", "")
        for h in payload.get("headers", [])
    }


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode(
        "utf-8", errors="replace"
    )


def _extract_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode(part["body"]["data"])
    for part in payload.get("parts", []):
        body = _extract_body(part)
        if body:
            return body
    return ""


@mcp.tool()
def list_messages(query: str = "", max_results: int = 10) -> dict:
    """Lista mensajes de Gmail. `query` usa la sintaxis de busqueda de Gmail
    (ej: 'is:unread', 'from:alguien@x.com', 'newer_than:2d')."""
    res = (
        gmail()
        .users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    out: list[dict] = []
    for m in res.get("messages", []):
        meta = (
            gmail()
            .users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        h = _headers(meta.get("payload", {}))
        out.append(
            {
                "id": m["id"],
                "threadId": m.get("threadId"),
                "from": h.get("from", ""),
                "subject": h.get("subject", ""),
                "date": h.get("date", ""),
                "snippet": meta.get("snippet", ""),
            }
        )
    return {"query": query, "count": len(out), "messages": out}


@mcp.tool()
def get_message(message_id: str) -> dict:
    """Devuelve el contenido completo de un mensaje por su ID."""
    msg = (
        gmail()
        .users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    h = _headers(payload)
    return {
        "id": msg.get("id"),
        "threadId": msg.get("threadId"),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "subject": h.get("subject", ""),
        "date": h.get("date", ""),
        "labels": msg.get("labelIds", []),
        "body": _extract_body(payload),
    }


@mcp.tool()
def send_message(to: str, subject: str, body: str, html: str = "") -> dict:
    """Envia un email. `to` puede ser una o varias direcciones separadas por coma.
    Si pasas `html`, el correo lleva una version HTML (con `body` como texto plano)."""
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = (
        gmail()
        .users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    return {"id": sent.get("id"), "threadId": sent.get("threadId"), "status": "sent"}


@mcp.tool()
def reply_message(message_id: str, body: str, html: str = "") -> dict:
    """Responde a un mensaje dentro de su mismo hilo (thread), citando cabeceras.
    Si pasas `html`, la respuesta lleva version HTML (con `body` como texto plano)."""
    original = (
        gmail()
        .users()
        .messages()
        .get(userId="me", id=message_id, format="metadata",
             metadataHeaders=["From", "To", "Subject", "Message-ID", "References"])
        .execute()
    )
    h = _headers(original.get("payload", {}))
    subject = h.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    references = h.get("references", "")
    message_id_header = h.get("message-id", "")

    msg = EmailMessage()
    msg["To"] = h.get("from", "")
    msg["Subject"] = subject
    if message_id_header:
        msg["In-Reply-To"] = message_id_header
        msg["References"] = (references + " " + message_id_header).strip()
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = (
        gmail()
        .users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": original.get("threadId")})
        .execute()
    )
    return {"id": sent.get("id"), "threadId": sent.get("threadId"), "status": "replied"}


@mcp.tool()
def list_labels() -> dict:
    """Lista las etiquetas disponibles en la cuenta."""
    res = gmail().users().labels().list(userId="me").execute()
    labels = [{"id": l["id"], "name": l["name"], "type": l.get("type")} for l in res.get("labels", [])]
    return {"count": len(labels), "labels": labels}


@mcp.tool()
def modify_labels(message_id: str, add: str = "", remove: str = "") -> dict:
    """Anade/quita etiquetas a un mensaje. `add`/`remove` son IDs de etiqueta
    separados por coma (ej: UNREAD, STARRED, INBOX o un label custom)."""
    add_ids = [x.strip() for x in add.split(",") if x.strip()]
    remove_ids = [x.strip() for x in remove.split(",") if x.strip()]
    res = (
        gmail()
        .users()
        .messages()
        .modify(userId="me", id=message_id, body={"addLabelIds": add_ids, "removeLabelIds": remove_ids})
        .execute()
    )
    return {"id": res.get("id"), "labels": res.get("labelIds", [])}


@mcp.tool()
def trash_message(message_id: str) -> dict:
    """Mueve un mensaje a la papelera."""
    res = gmail().users().messages().trash(userId="me", id=message_id).execute()
    return {"id": res.get("id"), "status": "trashed"}


if __name__ == "__main__":
    mcp.run()
