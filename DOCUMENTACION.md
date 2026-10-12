# MCP de Gmail — Conceptos, porqués y diagramas

Documento de estudio de lo que construimos. Explica **qué es cada pieza**,
**por qué** existe cada paso/config, y cómo **fluye** la información de punta a
punta.

---

## Índice

1. [Glosario de conceptos](#1-glosario-de-conceptos)
2. [Arquitectura general (diagrama)](#2-arquitectura-general)
3. [Flujo de autenticación OAuth (una sola vez)](#3-flujo-de-autenticación-oauth-una-sola-vez)
4. [Flujo de uso (cada mensaje)](#4-flujo-de-uso-cada-mensaje)
5. [Jerarquía de Google Cloud](#5-jerarquía-de-google-cloud)
6. [Por qué de cada paso de Google Cloud](#6-por-qué-de-cada-paso-de-google-cloud)
7. [Por qué de cada archivo del proyecto](#7-por-qué-de-cada-archivo-del-proyecto)
8. [Por qué de cada campo del config de opencode](#8-por-qué-de-cada-campo-del-config-de-opencode)
9. [Testing vs Producción y el token de 7 días](#9-testing-vs-producción)
10. [Seguridad](#10-seguridad)

---

## 1. Glosario de conceptos

### MCP (Model Context Protocol)
Es un **protocolo estándar** para que una IA (el modelo) pueda *usar herramientas
externas* de forma uniforme. Antes cada integración era a medida; MCP define un
contrato común: el modelo pide "ejecutá la tool X con estos argumentos" y recibe
un resultado. Es como un "USB-C para herramientas de IA".

### Cliente MCP / Host
El programa que corre el modelo y muestra las tools. En nuestro caso: **opencode**
(también lo serían Claude Desktop, Antigravity, etc.). Es quien *arranca* y
*habla* con el servidor MCP.

### Servidor MCP
El programa que **expone las tools**. En nuestro caso: `server.py`. No decide
nada por sí solo: espera órdenes del cliente y las ejecuta (leer correo, enviar,
etc.).

> Analogía: el cliente MCP es el **teléfono**, el servidor MCP es la **centralita**
> que sabe hacer las llamadas, y las tools son los **botones**.

### Transporte: stdio vs HTTP
Cómo se comunican cliente y servidor:
- **stdio** (el nuestro): el cliente lanza el servidor como **subproceso** y se
  hablan por *entrada/salida estándar* (stdin/stdout). Todo local, sin red, sin
  puertos. Más seguro.
- **HTTP/streamable**: el servidor es un servicio de red en una URL. Es lo que usa
  el MCP remoto de Google.

### Tool (herramienta)
Una función concreta que el modelo puede invocar, con un nombre y argumentos
tipados. Las nuestras: `list_messages`, `get_message`, `send_message`,
`list_labels`, `modify_labels`, `trash_message`.

### OAuth 2.0
El marco de autorización de Google. Permite que **una app** acceda a **tu cuenta**
**sin que le des tu contraseña**: le das un permiso limitado ("este carnet puede
leer tu correo"), revocable en cualquier momento.

### Proyecto de Google Cloud
Un contenedor en Google donde viven tus credenciales, APIs habilitadas y cuotas.
Todo OAuth necesita uno porque el "carnet" (cliente) se registra ahí.

### Pantalla de consentimiento (consent screen)
La pantalla que ve el usuario: *"**gmail-mcp** quiere acceder a tu cuenta"*. Define
quién es la app, a qué usuarios se permite, y qué scopes pide.

### Cliente OAuth (`client_id` / `client_secret`)
La **identidad registrada** de la app. Es el "carnet" que Google conoce.
- `client_id`: público, identifica a la app.
- `client_secret`: en apps Desktop no es un secreto real (Google asume que la app
  instalada no puede guardar secretos); la verdadera protección es el
  consentimiento por-usuario.

### Redirect URI / loopback
A dónde vuelve Google después de que aceptás. En apps Desktop se usa
`http://localhost:PUERTO/`: `auth_setup.py` levanta un mini-servidor local, Google
redirige ahí con un `code`, y el script lo canjea por un token. Por eso "se abre
el navegador y listo".

### Scopes
Los **permisos concretos** que pedís. Los nuestros:
- `gmail.readonly` → leer
- `gmail.send` → enviar
- `gmail.modify` → modificar (mover, marcar leído, archivar)
- `gmail.labels` → administrar etiquetas

### Access token / Refresh token
- **Access token**: credencial de corta vida (≈1 h) que se manda en cada request.
- **Refresh token**: credencial de larga vida que se usa para pedir *nuevos*
  access tokens cuando expiran. Es lo que hace que no tengas que loguearte cada
  hora. Se guarda en `token.json`.

### Testing vs Producción
Estado de publicación de la app. Afecta **quién** puede usarla y **si el refresh
token caduca**. Ver sección 9.

### ¿Por qué existe la "app"? (acceso delegado) — concepto clave
Esta es la idea que más cuesta y la que explica **todo** el montaje:

La **app (cliente OAuth) existe para que Google sepa *quién* le está pidiendo
acceso en tu nombre**, sin usar tu contraseña. OAuth es un modelo de **acceso
delegado**: vos *delegás* en la app el poder de tocar tu correo. Para eso Google
necesita una identidad **responsable y revocable** a la que asociar el token —
esa identidad es la app.

Se combinan **dos piezas**:

1. **La app** = la *identidad* ("gmail-mcp") + sus llaves → responde **¿quién pide?**
2. **Tu consentimiento** = el permiso → responde **¿a qué cuenta y con qué scopes?**

El flujo, entonces, es:

```
   la app pide  →  vos aceptás  →  Google emite un token
                                    atado a (la app + TU cuenta)
```

El token sirve **solo para esa dupla**. Si revocás el acceso, el token muere
aunque la app siga existiendo. Si otra persona usa la misma app, obtiene un token
de **su** cuenta, nunca de la tuya.

Dicho en una frase: *la app se creó para que tu herramienta pueda **autenticarse
como app** ante Google y, con tu permiso, **obtener un token de tu Gmail** — sin
conocer tu contraseña.* Eso es justo lo que hace `auth_setup.py`, y es lo que
habilita que `server.py` lea o envíe correo después.

---

## 2. Arquitectura general

```
┌──────────────────────────────────────────────────────────────────────┐
│                         TU MÁQUINA (local)                             │
│                                                                        │
│   ┌────────────────────┐   stdio (stdin/stdout)   ┌─────────────────┐  │
│   │   Cliente MCP      │ ◄──────────────────────► │  Servidor MCP   │  │
│   │   (opencode)       │   JSON-RPC sobre pipes   │  server.py      │  │
│   │                    │                          │                 │  │
│   │  - corre el modelo │                          │  tools:         │  │
│   │  - ofrece las tools│                          │  list_messages  │  │
│   └─────────┬──────────┘                          │  send_message   │  │
│             │                                     │  ...            │  │
│             │                                     └────────┬────────┘  │
│             │                                              │           │
│             │                                     lee token.json       │
│             │                                              │           │
│             │                                     ┌────────▼────────┐  │
│             │                                     │ credentials/    │  │
│             │                                     │  token.json     │  │
│             │                                     └─────────────────┘  │
└─────────────┼──────────────────────────────────────────────────────────┘
              │                                            │
       (nada sale del equipo por el modelo)         HTTPS (Gmail API)
                                                            │
                                                            ▼
                                          ┌─────────────────────────────────┐
                                          │        GOOGLE (nube)            │
                                          │  Gmail API  ◄──►  tu buzón      │
                                          │  Valida el access token         │
                                          └─────────────────────────────────┘
```

**Clave:** el modelo nunca ve tu contraseña. El servidor local pide a la nube solo
lo necesario, autenticado con el token.

---

## 3. Flujo de autenticación OAuth (una sola vez)

```
  auth_setup.py        Navegador           Google (accounts)      Gmail API
       │                    │                     │                  │
       │ lee client_id/     │                     │                  │
       │ secret del JSON    │                     │                  │
       │                    │                     │                  │
       │ abre URL de        │                     │                  │
       │ consentimiento ───►│                     │                  │
       │                    │  elegís cuenta +    │                  │
       │                    │  "Permitir" ───────►│                  │
       │                    │                     │ valida           │
       │                    │  redirige a         │                  │
       │                    │  localhost:PUERTO/?code=XXX ─┐        │
       │◄───────────────────┘                     │         │        │
       │  recibe el "code"  ◄──────────────────────────────┘        │
       │                    │                     │                  │
       │ canjea code ───────────────────────────►│                  │
       │  por access+refresh token               │                  │
       │◄────────────────────────────────────────┘                  │
       │                    │                     │                  │
       │ guarda credentials/token.json            │                  │
       │                    │                     │                  │
  (fin: nunca más este paso, salvo que caduque)
```

Puntos para entender:
- El **navegador** es solo para que *vos* aceptes; los tokens viajan por
  `localhost`, no pasan por terceros.
- El **`code`** es de un solo uso y de vida muy corta.
- Desde acá, `token.json` permite operar sin volver a loguearte (usa el refresh
  token), siempre que la app esté en Producción.

---

## 4. Flujo de uso (cada mensaje)

```
  Usuario        opencode         server.py          Gmail API         tu buzón
    │               │                │                   │                │
    │ "lista mis    │                │                   │                │
    │  no leídos" ──►│               │                   │                │
    │               │ decide usar    │                   │                │
    │               │ list_messages  │                   │                │
    │               │ tool call ────►│                   │                │
    │               │                │ carga token.json  │                │
    │               │                │ (refresca si hace │                │
    │               │                │  falta) ─────────►│                │
    │               │                │  GET messages ───────────────────►│
    │               │                │◄─────────────── lista ────────────┘
    │               │◄── resultado ──│                   │                │
    │◄─ texto final ─│                │                   │                │
```

Todo ocurre **en tu equipo** salvo el HTTPS puntual contra Gmail. El modelo nunca
"entra" a tu correo: pide a `server.py`, que actúa con tu token.

---

## 5. Jerarquía de Google Cloud

```
Proyecto (gmail-mcp)              ← contenedor de todo
│
├── APIs habilitadas
│     └── Gmail API               ← la que usamos (gmail.googleapis.com)
│
├── Google Auth Platform
│     ├── Branding                ← nombre, logo, email de soporte
│     ├── Audience                ← Externo/Interno, test users, estado
│     │     └── Publishing status: Testing | In production
│     └── Data Access (scopes)    ← permisos que la app puede pedir
│
└── Credenciales
      └── OAuth Client (Desktop)  ← client_id + client_secret (el JSON)
            └── genera, tras el login, el token.json del usuario
```

---

## 6. Por qué de cada paso de Google Cloud

| Paso | Por qué es necesario |
|---|---|
| **Crear proyecto** | Todo cliente OAuth debe pertenecer a un proyecto; ahí viven las APIs, cuotas y credenciales. |
| **Habilitar Gmail API** | El endpoint `gmail.googleapis.com` está apagado por defecto. Sin habilitarlo, cualquier request devuelve error. |
| **Pantalla de consentimiento** | Es la pantalla de permisos y define *quién* puede usar la app y *qué* scopes. Sin ella no se puede crear el cliente. |
| **Usuarios de prueba** | Mientras esté en "Testing", Google solo permite autenticar a cuentas que figuren ahí. Si no te agregás, te rechaza. |
| **Cliente OAuth tipo Desktop** | Es el "carnet". El tipo Desktop usa *loopback* (`localhost`), ideal para una app local como la tuya sin necesidad de dominio ni servidor público. |
| **Descargar el JSON** | Ahí están tu `client_id`/`client_secret`, que `auth_setup.py` necesita para iniciar el flujo. |
| **Autenticar (navegador)** | Le dice a Google "esta persona autoriza a esta app a tocar su cuenta con estos scopes". Genera `token.json`. |

---

## 7. Por qué de cada archivo del proyecto

```
~/gmail-mcp/
├── server.py          El servidor MCP. Define los 6 "botones" (tools) y habla
│                      Gmail API usando el token. Arranca con `mcp.run()` (stdio).
│
├── auth_setup.py      El "login". Hace el baile OAuth una vez y escribe
│                      credentials/token.json. El server NUNCA abre el navegador;
│                      eso lo hace solo este script.
│
├── requirements.txt   Dependencias: `mcp` (SDK), `google-api-python-client`
│                      (cliente de Gmail), `google-auth*` (OAuth y refresh).
│
├── test_protocol.py   Verifica el protocolo MCP real: arranca server.py como
│                      subproceso y hace initialize + tools/list + un call.
│
├── test_tools.py      Verifica la lógica de cada tool con la API de Gmail
│                      simulada (sin red ni credenciales).
│
└── credentials/       Secretos. Se mantiene con permisos 600.
    ├── gcp-oauth.keys.json   client_id/secret (del Paso 4 de Google Cloud)
    └── token.json            access+refresh token de TU cuenta
```

Concepto central: **separación de responsabilidades**. Autenticar (`auth_setup.py`)
es distinto de servir (`server.py`). El server asume que ya existe un `token.json`
válido; si no, lanza un error claro (`ToolError`).

---

## 8. Por qué de cada campo del config de opencode

Archivo `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",   // validación/autocompletado en el editor
  "mcp": {                                          // sección de servidores MCP
    "gmail": {                                      // el nombre que le damos (aparece en las tools)
      "type": "local",                              // es un programa local (no remoto por URL)
      "command": [                                  // cómo arrancarlo: comando + args (array!)
        "/home/kali/gmail-mcp/.venv/bin/python",    //   1) el python del venv (con las deps)
        "/home/kali/gmail-mcp/server.py"            //   2) el script del servidor
      ],
      "enabled": true                               // activado
    }
  }
}
```

- `type: local` → opencode lanzará ese comando como **subproceso** y hablará
  stdio con él. (Si fuera remoto sería `type: remote` + `url`.)
- Se usa la **ruta absoluta** del python del venv para no depender del `PATH` ni
  del entorno al arrancar.
- Se lee **solo al iniciar** opencode → hay que **reiniciar** tras cambiarlo.

---

## 9. Testing vs Producción

| | Testing | Producción (sin verificar) |
|---|---|---|
| Quién entra | solo los *test users* listados (máx 100) | cualquiera con su cuenta |
| **Refresh token** | **caduca a los 7 días** | **no caduca** |
| Aviso al entrar | normalmente directo | "Google no verificó esta app" |
| Verificación de Google | no | puede requerirse (Gmail = scopes restringidas) |

**Por qué el "7 días"**: es una medida de seguridad de Google para apps no
publicadas, para limitar el daño de tokens filtrados.

**Implicancia práctica para nosotros**: si quedás en **Testing**, cada ~7 días
tenés que correr `auth_setup.py` de nuevo (20 segundos, vuelve a salir el
navegador). Si querés evitarlo, hay que publicar la app (y con scopes de Gmail,
Google puede pedir verificación).

**Error común**: como el `client_secret` de una app Desktop no es realmente
secreto, "publicar" no expone tu correo: cada usuario que use la app solo accede a
**su propia** cuenta. Tu `token.json` sigue siendo local y privado.

---

## 10. Seguridad

- **`credentials/` nunca se comparte ni se sube a git.** Contiene secretos y tu
  token de acceso a Gmail.
- **Permisos mínimos**: si algún día solo querés leer, dejá únicamente
  `gmail.readonly` en `SCOPES` (en `auth_setup.py` y `server.py`).
- **El server es local (stdio)**: no abre puertos ni URLs; nadie de fuera puede
  alcanzarlo.
- **Revocación**: podés quitar el acceso en cualquier momento desde
  https://myaccount.google.com/permissions (o borrar `token.json`).
- **Prompt injection**: si el modelo procesa correos no confiables, esos correos
  podrían intentar "ordenarle" acciones. Revisá las acciones sensibles (enviar,
  borrar) antes de confirmarlas.

---

### Cómo reproducirlo desde cero (resumen)

1. Google Cloud → proyecto → habilitar **Gmail API**.
2. Pantalla de consentimiento (**Externo**) → agregarte como **test user**.
3. Crear credencial **Desktop app** → descargar JSON → `credentials/gcp-oauth.keys.json`.
4. `python auth_setup.py` → navegador → `credentials/token.json`.
5. Registrar el server en el cliente MCP (`opencode.jsonc`).
6. Reiniciar el cliente → usar las tools.
