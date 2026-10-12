# Security Policy

## Manejo de credenciales

Este proyecto accede a tu cuenta de Gmail mediante OAuth 2.0. Ten en cuenta:

- **Nunca** subas a git el directorio `credentials/` ni ningún archivo
  `*client_secret*.json`, `token.json`, `gcp-oauth.keys.json`, `.env`, `*.pem` o
  `*.key`. El `.gitignore` ya los excluye.
- `auth_setup.py` crea `token.json` con permisos `600`.
- **Mínimo privilegio**: los scopes se centralizan en [`config.py`](config.py) y se
  pueden ajustar con la variable de entorno `GMAIL_MCP_SCOPES` (por ejemplo,
  `https://www.googleapis.com/auth/gmail.readonly` para solo lectura).
- **Envío controlado**: `send_message` y `reply_message` pueden desactivarse con
  `GMAIL_MCP_ALLOW_SEND=0`. En ese modo queda disponible `create_draft` para
  redactar sin enviar.
- **Allowlist de destinatarios**: `GMAIL_MCP_ALLOWED_RECIPIENTS` restringe a qué
  direcciones se puede enviar/responder (vacío = sin restricción). Es la mitigación
  principal contra la exfiltración inducida por *prompt injection*.
- **Auditoría**: toda acción con efecto (envío, respuesta, papelera, etiquetas) se
  registra append-only en `state/audit.log` (JSON por línea, timestamp UTC).
- Revocá el acceso en cualquier momento desde
  <https://myaccount.google.com/permissions>.

## Alcance

El servidor es **local** y usa transporte **stdio**: se ejecuta como subproceso
del cliente MCP y no expone puertos ni endpoints de red.

## Riesgo de inyección de prompts

Al exponer un modelo a datos no confiables (correos, adjuntos), existe riesgo de
*indirect prompt injection*: contenido malicioso podría intentar provocar acciones
no deseadas. Mitigaciones incluidas:

- El cuerpo de `get_message` se marca con `untrusted_content: true` y el HTML se
  acota (`GMAIL_MCP_HTML_CAP`, con flag `html_truncated`).
- El envío puede desactivarse (`GMAIL_MCP_ALLOW_SEND=0`) o limitarse por allowlist
  (`GMAIL_MCP_ALLOWED_RECIPIENTS`) para frenar la exfiltración.
- Las acciones con efecto quedan en `state/audit.log`.

Aun así, revisá las acciones sensibles (enviar, borrar) antes de confirmarlas. Para
uso autónomo, preferí borradores (`GMAIL_MCP_ALLOW_SEND=0`) o una allowlist estricta.

## Reportar una vulnerabilidad

Si encontrás un problema de seguridad, abrí un *issue* privado de seguridad o
contactá al mantenedor en lugar de publicarlo como issue abierto.
