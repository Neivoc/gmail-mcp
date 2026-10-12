# Gmail MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-stdio-6E56CF.svg)](https://modelcontextprotocol.io)

Servidor [Model Context Protocol](https://modelcontextprotocol.io) **local** para Gmail.
Permite a cualquier cliente MCP (opencode, Claude Desktop, Cursor, …) **leer, buscar,
enviar y organizar** correo mediante OAuth 2.0, sin exponer tu contraseña.

- Transporte **stdio**: corre como subproceso local, sin abrir puertos ni URLs.
- Autenticación OAuth delegada; los tokens se refrescan solos.
- Credenciales aisladas en `credentials/` y excluidas de git.
- Envío **desactivable** y tool de **borrador** para mitigar *prompt injection*.

## Características

| Tool | Descripción |
| --- | --- |
| `list_messages` | Lista/busca mensajes (sintaxis de Gmail: `is:unread`, `from:…`, `newer_than:2d`). Usa *batch* para los metadatos. |
| `get_message` | Contenido completo: texto, HTML y metadatos de adjuntos. El cuerpo se marca como **contenido no confiable**. |
| `send_message` | Envía un correo; soporta **HTML**. Desactivable con `GMAIL_MCP_ALLOW_SEND=0`. |
| `create_draft` | Crea un **borrador** (no envía). Puede responder en un hilo con `in_reply_to`. |
| `reply_message` | Responde en el hilo (`In-Reply-To`/`References`), respeta `Reply-To` y evita responderte a ti mismo. |
| `list_labels` | Lista las etiquetas de la cuenta. |
| `modify_labels` | Añade/quita etiquetas (marcar leído, destacar, archivar…). |
| `trash_message` | Mueve un mensaje a la papelera. |

## Requisitos

- **Python 3.10+**
- **`mcp>=2.3.0`** — obligatorio. El código usa `mcp.server.mcpserver.MCPServer`, que
  no existe en la 1.x (ahí se llamaba `FastMCP`); con un `mcp` antiguo falla al importar.
- Un proyecto en Google Cloud con **Gmail API** habilitada y un **cliente OAuth de
  escritorio** (ver [Configuración](#configuración-de-google-cloud)).
- Un **navegador en la misma máquina** para autenticar (ver [Autenticación](#autenticación-una-sola-vez)).

## Instalación

**Linux / macOS**

```bash
git clone https://github.com/Neivoc/gmail-mcp.git
cd gmail-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/Neivoc/gmail-mcp.git
cd gmail-mcp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuración de Google Cloud

1. Crea un proyecto en <https://console.cloud.google.com>.
2. **APIs y servicios → Biblioteca** → habilita **Gmail API**.
3. **APIs y servicios → Pantalla de consentimiento de OAuth** → tipo **Externo** y
   añade tu cuenta como **usuario de prueba**.
4. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**
   → tipo **Aplicación de escritorio**.
5. Descarga el JSON y guárdalo como:

   ```
   credentials/gcp-oauth.keys.json
   ```

## Autenticación (una sola vez)

```bash
python auth_setup.py
```

Se abre el navegador; tras aceptar los permisos se genera `credentials/token.json`
(con `refresh_token`, se renueva automáticamente).

> **Navegador obligatorio:** `auth_setup.py` usa `flow.run_local_server(...)`, por lo
> que necesita un navegador en la **misma máquina**. En un servidor sin GUI/display no
> funciona tal cual: habría que hacer el flujo OAuth aparte y copiar `token.json`.

> **App en estado _Testing_:** el refresh token caduca **cada 7 días**. Para evitarlo,
> publica la app (Google Auth Platform → Audience → *Publish app*).

## Configuración por variables de entorno

Todo se centraliza en [`config.py`](config.py); no hace falta editar dos archivos.

| Variable | Por defecto | Descripción |
| --- | --- | --- |
| `GMAIL_MCP_SCOPES` | `gmail.modify gmail.send` | Scopes separados por espacio o coma. Para **solo lectura**: `https://www.googleapis.com/auth/gmail.readonly`. |
| `GMAIL_MCP_ALLOW_SEND` | `1` | `0`/`false`/`no` bloquea `send_message` y `reply_message` (el resto sigue funcionando). |

> Cambiar los scopes exige **volver a autenticar** (`python auth_setup.py`).
> `gmail.modify` ya incluye lectura y etiquetas; `gmail.send` se añade por robustez.

## Registrar en el cliente MCP

Usa rutas **absolutas** y el intérprete del entorno virtual.

**opencode** (`~/.config/opencode/opencode.jsonc`):

```jsonc
{
  "mcp": {
    "gmail": {
      "type": "local",
      "command": ["/ruta/absoluta/gmail-mcp/.venv/bin/python", "/ruta/absoluta/gmail-mcp/server.py"],
      "enabled": true,
      "environment": { "GMAIL_MCP_ALLOW_SEND": "1" }
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/ruta/absoluta/gmail-mcp/.venv/bin/python",
      "args": ["/ruta/absoluta/gmail-mcp/server.py"]
    }
  }
}
```

En Windows, el comando es `.venv\Scripts\python.exe`. Reinicia el cliente tras editar.

## Tests

No requieren credenciales ni conexión real a Gmail:

```bash
.venv/bin/python test_protocol.py   # handshake MCP real por stdio + tools/list
.venv/bin/python test_tools.py      # lógica de las 8 tools con la API simulada
```

`test_tools.py` cubre parseo de texto/HTML/adjuntos, *batch*, borradores, cabeceras de
respuesta, `Reply-To`, la evitación de auto-respuesta y el bloqueo de envío.
`test_protocol.py` arranca el servidor como subproceso y habla MCP de verdad.

## Seguridad

- `credentials/` contiene secretos y está en `.gitignore`. **Nunca** lo compartas.
- `token.json` se crea (y se reafirma tras cada refresh) con permisos `600`.
- **Mínimo privilegio**: ajusta los scopes con `GMAIL_MCP_SCOPES` (p. ej. solo
  `gmail.readonly` para lectura).
- **Anti prompt-injection**: el cuerpo de los correos se marca como contenido no
  confiable; usa `create_draft` y/o `GMAIL_MCP_ALLOW_SEND=0` para evitar envíos
  inducidos por correos maliciosos.
- Revoca el acceso cuando quieras desde <https://myaccount.google.com/permissions>.
- El servidor es local (stdio): no abre puertos ni endpoints de red.

Ver [SECURITY.md](SECURITY.md).

## Licencia

[MIT](LICENSE)
