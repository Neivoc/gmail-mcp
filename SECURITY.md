# Security Policy

## Manejo de credenciales

Este proyecto accede a tu cuenta de Gmail mediante OAuth 2.0. Ten en cuenta:

- **Nunca** subas a git el directorio `credentials/` ni ningún archivo
  `*client_secret*.json`, `token.json`, `gcp-oauth.keys.json`, `.env`, `*.pem` o
  `*.key`. El `.gitignore` ya los excluye.
- `auth_setup.py` crea `token.json` con permisos `600`.
- Usá el **principio de mínimo privilegio**: ajusta `SCOPES` en `auth_setup.py`
  y `server.py` a lo que realmente necesites (por ejemplo, solo `gmail.readonly`).
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
