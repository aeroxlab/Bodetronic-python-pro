# Bodega Chebitas - Panel directo + Apps Script + Google Sheets

Sistema Python/Render con panel independiente sin login ni admin. Entra directo a Bodega Chebitas.

## Estructura
- `main.py`: backend FastAPI + SQLite + sincronización hacia Apps Script.
- `static/index.html`: panel visual negro / verde neón.
- `Code.gs`: Apps Script para guardar respaldo en tu Google Sheet.
- `requirements.txt`: dependencias Render.
- `Procfile` / `render.yaml`: despliegue.

## Google Sheet vinculado
ID usado en `Code.gs`:

```text
1_drLSBzDs8fRas31qTp2C64nIeTzHcvu0HS13SiFCZM
```

## Paso 1: Apps Script
1. Abre tu Google Sheet.
2. Entra a **Extensiones > Apps Script**.
3. Borra el código que aparece.
4. Pega todo el contenido de `Code.gs`.
5. Guarda.
6. Ejecuta la función `setup` una vez y acepta permisos.
7. Ve a **Implementar > Nueva implementación**.
8. Tipo: **Aplicación web**.
9. Ejecutar como: **Yo**.
10. Quién tiene acceso: **Cualquier usuario**.
11. Copia la URL de la Web App.

## Paso 2: Render Environment Variables
En Render agrega:

```text
SHEET_WEBAPP_URL = URL_DE_TU_APPS_SCRIPT
SHEET_SECRET = chebitas-2026
BASE_URL = https://TU-SERVICIO.onrender.com
SUPPORT_WHATSAPP = 51992657332
```

## Paso 3: GitHub / Render
Sube todos los archivos a tu repositorio y en Render usa:

```text
Manual Deploy
Clear build cache & deploy
```

## Notas
SQLite trabaja rápido dentro de Render y Apps Script copia los datos a Google Sheets como respaldo. En Render Free los archivos subidos a `/uploads` podrían perderse en redeploys fuertes; para producción conviene luego guardar imágenes en Drive o Cloudinary.


## Ajuste de vista previa local
Si abres `static/index.html` en Acode, ahora se muestra una vista previa local del panel. Las funciones reales de guardar, editar, scanner, ventas, créditos y sincronización con Sheet deben probarse en Render porque dependen del backend Python.


## Corrección final solicitada
- Productos: campo de código de barras con botón Scaner.
- Fotos de referencia: galería, cámara, múltiples fotos, primera foto principal, agregar/eliminar.
- Inicio: métricas compactas arriba y accesos rápidos.
- Ventas/POS: scanner y foto/galería para encontrar producto y agregar al carrito rápido.
- Créditos/Fiados: scanner y foto/galería para llenar producto/precio rápido al agregar fiado.
- Link público: solo lectura para cliente; edición solo desde panel.
