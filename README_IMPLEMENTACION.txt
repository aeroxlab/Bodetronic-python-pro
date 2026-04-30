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


CORRECCIÓN - RECONOCIMIENTO VISUAL Y ENTRENAMIENTO:
- Se reemplazó la comparación simple por una firma visual mejorada local:
  promedio, diferencias, bordes y color.
- Se recalculan firmas antiguas al comparar, sin pedir volver a registrar productos.
- Si no hay coincidencia segura, se muestran posibles productos y permite entrenar con la foto capturada.
- En editar producto se puede cambiar foto principal y agregar más fotos de referencia.
- El scanner/cámara queda más limpio y con menos texto.
- No se alteró la lógica general de clientes, QR, pagos, sponsor, ventas, créditos ni stock.


CORRECCIÓN EXTRA - VISIÓN V3 Y RESULTADO EMERGENTE:
- La comparación ahora revisa más detalles: forma general, bordes, color, zonas de etiqueta,
  patrones parecidos a letras/textos, códigos visibles, colores dominantes y partes del producto.
- Se recalculan firmas antiguas a la nueva firma v3 automáticamente cuando se compara.
- El resultado de cámara/galería aparece en una pantalla emergente con:
  foto tomada/cargada, producto encontrado o posibles productos, puntaje visual y botones de acción.
- Si no hay coincidencia segura, permite entrenar el producto con la foto capturada.
- Esto sigue siendo reconocimiento local sin API externa. Para leer texto exacto como OCR real
  o reconocer marcas con IA avanzada se puede conectar luego una API de visión.


CORRECCIÓN - FOTOS Y COMPARACIÓN MÁS ESTRICTA:
- Cada foto registrada del producto ahora muestra una X para eliminarla individualmente.
- Desde editar producto se puede borrar todas las fotos o borrar el producto completo.
- La comparación visual ahora es más estricta para evitar falsos positivos:
  no acepta solo forma parecida; exige concordancia en color, etiqueta, texto/marca, forma y detalles visuales.
- Si no hay igualdad segura, no marca "Producto encontrado"; solo muestra posibles coincidencias para entrenar.
- No se alteró la lógica general del sistema.
