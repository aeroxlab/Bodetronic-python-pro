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


CORRECCIÓN URGENTE - EVITAR FALSOS POSITIVOS:
- Se agregó firma visual V4 enfocada en color vivo de etiqueta, letras/marca, zona central, forma y bordes.
- Productos con forma parecida ya no se aceptan si no coinciden etiqueta/color/texto/marca.
- Para decir "Producto encontrado" ahora exige match muy fuerte o soporte por foto principal/varias referencias.
- Si una Kola Real amarilla/verde se compara contra agua San Carlos azul, debe quedar como "No hay coincidencia segura".
- Esto aplica también para galletas, snacks y productos con empaques similares.


CORRECCIÓN V5 - MISMO PRODUCTO Y FOTOS SINCRONIZADAS:
- Limpieza automática interna de fotos: no aparece ningún botón extra para el usuario.
- Si product.image_url queda apuntando a una foto antigua/oculta, el sistema lo corrige solo.
- La cámara compara SOLO contra fotos visibles registradas en el producto.
- Si una foto fue eliminada con X, ya no participa en la comparación.
- Se eliminan automáticamente referencias duplicadas o sin archivo real.
- Se recalculan huellas visuales V4 automáticamente.
- La aceptación de coincidencia ahora es más estricta:
  botella no coincide con otra botella solo por forma; debe coincidir etiqueta, color, marca/letras,
  zona central, forma, tamaño visual y foto principal o varias referencias.
- Si no es el mismo producto, devuelve "No hay coincidencia segura".
- Se agregó anti-caché a imágenes de uploads para evitar ver fotos antiguas del navegador/Render.


CORRECCIÓN V6 - MAYOR PESO A FOTO PRINCIPAL:
- La foto principal del producto ahora tiene mayor peso en la comparación.
- Si una coincidencia viene de la imagen principal, se prioriza sobre referencias secundarias.
- Si una coincidencia viene de una foto secundaria, se exige apoyo de la principal o varias referencias.
- Esto mejora el reconocimiento sin alterar la lógica general del sistema.


CORRECCIÓN V7 - COMPARACIÓN MÁS PRECISA SIN FALSOS POSITIVOS:
- Se afinó la comparación de color de etiqueta usando intersección de tonos, no solo distancia general.
- Esto permite reconocer mejor el mismo producto tomado desde otro ángulo/luz.
- Se mantiene la regla anti-confusión: no acepta productos diferentes solo por tener forma parecida.
- Para confirmar un producto exige etiqueta/color y marca-letras o varias referencias del mismo producto.
- Se agregó margen entre productos: si dos productos se parecen demasiado, no confirma automáticamente.
- La foto principal conserva mayor peso y las fotos secundarias sirven como apoyo de entrenamiento.


CORRECCIÓN V8 - SCANNER TIPO MINIMARKET:
- El panel Scanner/Cámara ahora tiene 2 opciones principales: buscar por código de barras y buscar por imagen.
- Ambas opciones usan cámara.
- Código de barras: cámara en vivo, detecta el número automáticamente, reproduce pitido y abre popup del producto.
- Imagen: cámara en vivo, captura frames internos temporales y abre popup solo cuando detecta coincidencia segura.
- Se mantiene búsqueda manual por nombre/código.
- En registro y edición de producto, el campo código de barras ahora permite escritura manual o escaneo con cámara para llenar el número automáticamente.
- Los frames internos de la cámara no entrenan ni guardan productos automáticamente; solo comparan temporalmente.
- No se alteró la lógica general de clientes, productos, stock, pagos, QR, publicidad, créditos ni ventas.


CORRECCIÓN V9 - LINK PÚBLICO MÓVIL Y STOCK EN FIADO:
- El link público de Créditos/Cuentas ahora tiene diseño responsive para Android/iOS.
- En móvil, la tabla se convierte en tarjetas ordenadas para que no se desborde.
- Al agregar un fiado con producto registrado, se descuenta stock del mismo inventario.
- Si el fiado se ingresa manual y coincide exactamente con un producto único por nombre, código interno, referencia o código de barras, también descuenta stock.
- No hace coincidencias aproximadas para no descontar un producto equivocado.
- Se mantiene la lógica general del sistema.

CORRECCIÓN V11 - SMART CHECKOUT / CÁMARA EN VIVO:
- Se implementó el flujo visual más parecido a la referencia de reconocimiento de productos.
- La cámara por imagen queda abierta y muestra REC, recuadro verde, etiqueta de estado y animación de encerrado del objeto.
- La comparación ya no manda toda la pantalla: recorta internamente el área central del recuadro para comparar el producto enfocado.
- Se agregó botón Pausar escaneo / Reanudar escaneo y botón Parar.
- Si detecta el mismo producto con seguridad, hace pitido y abre popup.
- Código de barras se mantiene como método principal.
- En Punto de venta se agregó cámara por código y cámara por imagen para agregar productos entrenados al carrito.
- Las fotos subidas por producto siguen funcionando como entrenamiento/referencia.
- Se mantiene la lógica general de clientes, stock, ventas, pagos, QR, créditos y publicidad.
