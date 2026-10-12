# Credenciales (local, no versionada)

Esta carpeta guarda los secretos de tu Gmail. **Todo su contenido real está
excluido de git** (ver `.gitignore`); solo se versionan las plantillas de ejemplo.

## Archivos

| Archivo | Quién lo crea | Descripción |
| --- | --- | --- |
| `gcp-oauth.keys.json` | tú (descargado de Google Cloud) | Credenciales OAuth de tipo *Aplicación de escritorio*. Copia de `gcp-oauth.keys.json.example`. |
| `token.json` | `auth_setup.py` | Token de acceso + refresh de **tu** cuenta. Permisos `600`. **Nunca** lo compartas ni lo subas. |

## Cómo obtener `gcp-oauth.keys.json`

1. Google Cloud Console → proyecto → **APIs y servicios → Credenciales →
   Crear credenciales → ID de cliente de OAuth → Aplicación de escritorio**.
2. Descarga el JSON y guárdalo aquí como `gcp-oauth.keys.json`:

   ```bash
   cp credentials/gcp-oauth.keys.json.example credentials/gcp-oauth.keys.json
   # …y reemplaza los placeholders por tus valores reales (o sobreescribí el
   # archivo con el JSON descargado de Google Cloud).
   ```

   > Formato de los valores reales (los placeholders son neutros a propósito):
   > `client_id` es `NNNNNNNNNN-xxxxxxxx....apps.googleusercontent.com` y
   > `client_secret` suele empezar con `GOCSPX-`. No los pegues en el repo.

3. Ejecuta `python auth_setup.py` para generar `token.json`.

> Si esta carpeta no existe al clonar, créala (`mkdir credentials`) — `config.py`
> espera leer los archivos desde aquí.
