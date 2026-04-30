BODETRONIC PYTHON PRO - PROYECTO FINAL CORREGIDO

Base preparada para subir primero a GitHub y luego a Render.

Estructura:
- main.py
- static/index.html
- uploads/.gitkeep
- requirements.txt
- Procfile
- render.yaml
- .env.example
- .gitignore

Correcciones aplicadas sin alterar la lógica general:
1. Cámara / Scanner:
   - Tomar foto del producto.
   - Subir archivo desde galería.
   - Escanear código de barras con cámara.
   - Subir imagen del código de barras.
   - Búsqueda manual por nombre, código interno, referencia o código de barras.

2. Registro de producto:
   - Tomar foto.
   - Subir una o más fotos desde galería.
   - La primera foto queda como foto principal.
   - Las demás fotos quedan como referencias para entrenar comparación visual.
   - Campo para código de barras manual.
   - Opción de leer código de barras con cámara o imagen.

3. Vinculación producto + código de barras:
   - Si el sistema detecta un producto entrenado por imagen y también lee código de barras, permite vincular ese código al producto.
   - Endpoint agregado: /api/products/{product_id}/link-barcode
   - No modifica stock, precios, ventas, créditos ni lógica principal.

4. Login / carga inicial:
   - Se incluye static/index.html para que Render cargue la pantalla principal.
   - Se agrega fallback para que si se abre una ruta interna como /login o /panel, vuelva a cargar el index sin romper el frontend.
   - Recuerda que Render Free puede demorar al primer ingreso por cold start.

5. GitHub:
   - Se incluye uploads/.gitkeep para que GitHub conserve la carpeta uploads aunque esté vacía.

Render:
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT

Variables recomendadas en Render:
APP_NAME=Bodetronic
SECRET_KEY=una_clave_larga_segura
MASTER_USER=73221820
MASTER_PASS=jdiazg20
SUPPORT_WHATSAPP=51992657332
BASE_URL=https://tu-app.onrender.com
UPLOAD_DIR=uploads

Nota importante:
Si usas Render Free sin disco persistente, los archivos subidos a uploads pueden perderse cuando Render reinicie o redepliegue. Para producción se recomienda Render Disk, Cloudinary, Google Drive o S3.
