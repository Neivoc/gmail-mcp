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


def _load_allowed_recipients() -> frozenset[str]:
    """Allowlist de destinatarios para send_message/reply_message.

    `GMAIL_MCP_ALLOWED_RECIPIENTS` = direcciones separadas por coma o espacio.
    Si esta VACIA, se permite cualquier destinatario (comportamiento por defecto).
    Si tiene valores, SOLO se puede enviar a esas direcciones: mitiga la
    exfiltracion inducida por prompt injection al leer correo no confiable.
    """
    raw = os.environ.get("GMAIL_MCP_ALLOWED_RECIPIENTS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(a.lower() for a in raw.replace(",", " ").split() if a)


ALLOWED_RECIPIENTS = _load_allowed_recipients()

# Limite maximo de la API de Gmail para maxResults.
MAX_RESULTS_CAP = 500

# Tope de caracteres devueltos para body_html en get_message. El HTML de un
# correo es contenido no confiable y puede ser enorme: truncarlo evita inflar
# el contexto del modelo. Configurable con GMAIL_MCP_HTML_CAP.
try:
    BODY_HTML_CAP = int(os.environ.get("GMAIL_MCP_HTML_CAP", "200000"))
except ValueError:
    BODY_HTML_CAP = 200000

# Registro de auditoria de acciones con efecto (envios, respuestas, papelera,
# etiquetas). Append-only. El directorio state/ esta en .gitignore.
AUDIT_LOG = BASE_DIR / "state" / "audit.log"
