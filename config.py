"""Configuracion central del Gmail MCP.

Un unico lugar para rutas, scopes y flags. `server.py` y `auth_setup.py`
importan de aqui, de modo que cambiar los scopes no exige tocar dos archivos.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CRED_DIR = BASE_DIR / "credentials"
CLIENT_SECRET_FILE = CRED_DIR / "gcp-oauth.keys.json"
TOKEN_FILE = CRED_DIR / "token.json"

# `gmail.modify` ya cubre lectura, etiquetas y (segun Google) envio. Se anade
# `gmail.send` de forma explicita por robustez. Para modo solo-lectura usa
# unicamente gmail.readonly.
_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _load_scopes() -> list[str]:
    """Scopes configurables por entorno: GMAIL_MCP_SCOPES separados por espacio o coma."""
    raw = os.environ.get("GMAIL_MCP_SCOPES", "").strip()
    if raw:
        return [s for s in raw.replace(",", " ").split() if s]
    return list(_DEFAULT_SCOPES)


SCOPES = _load_scopes()

# Si es "0"/"false"/"no", se bloquean send_message y reply_message (se puede
# seguir usando create_draft). Util para reducir el riesgo de envios inducidos
# por prompt injection al leer correos.
SEND_ENABLED = os.environ.get("GMAIL_MCP_ALLOW_SEND", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

# Limite maximo de la API de Gmail para maxResults.
MAX_RESULTS_CAP = 500
