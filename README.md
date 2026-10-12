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

## Características

| Tool | Descripción |
| --- | --- |
| `list_messages` | Lista/busca mensajes con la sintaxis de Gmail (`is:unread`, `from:…`, `newer_than:2d`). |
| `get_message` | Devuelve el contenido completo (cabeceras + cuerpo) de un mensaje. |
| `send_message` | Envía un correo; soporta versión **HTML** además del texto plano. |
| `reply_message` | Responde dentro del hilo (`In-Reply-To`/`References`), con soporte HTML. |
| `list_labels` | Lista las etiquetas de la cuenta. |
| `modify_labels` | Añade/quita etiquetas (ej. marcar leído, destacar, archivar). |
| `trash_message` | Mueve un mensaje a la papelera. |

## Requisitos

- Python **3.10+**
- Un proyecto en Google Cloud con **Gmail API** habilitada y un **cliente OAuth de
  escritorio** (ver [Configuración](#configuración-de-google-cloud)).

## Instalación

```bash
git clone https://github.com/Neivoc/gmail-mcp.git
cd gmail-mcp
python3 -m venv .venv
source .venv/bin/activate
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

> **Nota:** mientras la app OAuth esté en estado *Testing*, el refresh token caduca
> cada 7 días. Publica la app (Google Auth Platform → Audience → *Publish app*) para
> evitarlo.

## Registrar en el cliente MCP

Usa rutas **absolutas** y el intérprete del entorno virtual.

**opencode** (`~/.config/opencode/opencode.jsonc`):

```jsonc
{
  "mcp": {
    "gmail": {
      "type": "local",
      "command": ["/ruta/absoluta/gmail-mcp/.venv/bin/python", "/ruta/absoluta/gmail-mcp/server.py"],
      "enabled": true
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

Reinicia el cliente para que cargue el servidor.

## Tests

No requieren credenciales ni conexión real a Gmail:

```bash
.venv/bin/python test_protocol.py   # handshake MCP real por stdio + tools/list
.venv/bin/python test_tools.py      # lógica de las tools con la API simulada
```

## Seguridad

- `credentials/` contiene secretos y está en `.gitignore`. **Nunca** lo compartas.
- `token.json` se crea con permisos `600`.
- Aplica el principio de **mínimo privilegio**: si solo vas a leer, deja únicamente
  `gmail.readonly` en `SCOPES` (`auth_setup.py` y `server.py`).
- Revoca el acceso cuando quieras desde <https://myaccount.google.com/permissions>.
- El servidor es local (stdio): no abre puertos ni endpoints de red.

## Licencia

[MIT](LICENSE)
