#!/usr/bin/env python3
"""Flujo OAuth de Google para Gmail MCP.

Uso:
    python auth_setup.py

Requiere que hayas creado credenciales OAuth (tipo "Desktop app") en
Google Cloud Console y guardado el JSON en:
    credentials/gcp-oauth.keys.json

Al terminar genera:
    credentials/token.json
"""

from __future__ import annotations

import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import CLIENT_SECRET_FILE, CRED_DIR, SCOPES, TOKEN_FILE


def main() -> int:
    CRED_DIR.mkdir(parents=True, exist_ok=True)

    if not CLIENT_SECRET_FILE.exists():
        print(f"[!] No encuentro {CLIENT_SECRET_FILE}")
        print("    Descarga el JSON OAuth (tipo 'Desktop app') desde Google")
        print("    Cloud Console y guardalo con ese nombre.")
        return 1

    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        TOKEN_FILE.chmod(0o600)

    print(f"[ok] Token guardado en {TOKEN_FILE}")
    print("[ok] Ya puedes arrancar el server MCP: python server.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
