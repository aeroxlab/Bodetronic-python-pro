BODETRONIC PYTHON PRO - CORRECCIÓN PUNTUAL

Base usada:
- main.py e index.html cargados por el usuario.
- No se rehizo la lógica general.
- Se conservaron clientes, diseño, publicidad/sponsor, QR, pagos, productos, stock, POS y créditos.

Correcciones aplicadas:
1) Cámara / galería:
- Botón Tomar foto.
- Botón Subir archivo desde galería.
- Reconocimiento visual contra fotos ya registradas.
- Si detecta producto, permite editarlo o mover stock.

2) Código de barras:
- Escanear con cámara usando BarcodeDetector cuando el navegador lo soporte.
- Subir imagen con código de barras.
- Escribir código manualmente.
- Buscar por código, nombre, referencia o código interno.
- Vincular el código detectado/buscado al producto.

3) Producto:
- Botón Editar en cada producto.
- Permite editar nombre, marca, código de barras, referencia, categoría, presentación, stock, stock mínimo, precio real, precio venta, vencimiento y notas.
- Si cambia stock por edición, registra movimiento AJUSTE_MANUAL.

4) Publicidad / sponsor:
- No se fuerza video a pantalla completa.
- Se agrega encaje de video/imagen: contain, cover o fill.
- Se agrega ubicación Franja/Banner en footer.
- Los videos/imágenes se encajan en un espacio tipo banner/franja.
- Mantiene opciones existentes de ticker, footer, flotante, tarjeta y ubicación.

5) GitHub / Render:
- Incluye uploads/.gitkeep para conservar carpeta uploads.
- Incluye requirements.txt, Procfile, render.yaml, .env.example y .gitignore.

Nota:
- BarcodeDetector depende del navegador. En Chrome Android suele funcionar; si no, usar código manual o subir imagen.
- En Render Free la primera carga puede demorar porque la app duerme.


CORRECCIÓN EXTRA - CÁMARA / GALERÍA:
- En registro de producto ya no se usa un solo selector con capture.
- Ahora hay botones separados:
  1) Tomar foto: abre cámara.
  2) Subir desde galería: abre archivos/galería y permite varias imágenes.
- Esto evita que Android abra solo cámara cuando el usuario quiere elegir imágenes.
