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
- Revocá el acceso en cualquier momento desde
  <https://myaccount.google.com/permissions>.

## Alcance

El servidor es **local** y usa transporte **stdio**: se ejecuta como subproceso
del cliente MCP y no expone puertos ni endpoints de red.

## Riesgo de inyección de prompts

Al exponer un modelo a datos no confiables (correos, adjuntos), existe riesgo de
*indirect prompt injection*: contenido malicioso podría intentar provocar acciones
no deseadas. Revisá siempre las acciones sensibles (enviar, borrar) antes de
confirmarlas.

## Reportar una vulnerabilidad

Si encontrás un problema de seguridad, abrí un *issue* privado de seguridad o
contactá al mantenedor en lugar de publicarlo como issue abierto.
