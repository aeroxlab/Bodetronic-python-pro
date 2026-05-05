/**
 * Bodega Chebitas / Bodetronic - Puente Google Sheets
 * Conecta Render + SQLite con Google Sheets usando Apps Script.
 */

const SHEET_ID = '1_drLSBzDs8fRas31qTp2C64nIeTzHcvu0HS13SiFCZM';
const SECRET = 'chebitas-2026';

const HEADERS = {
  Config: [
    'clave',
    'valor',
    'descripcion',
    'actualizado',
    'fecha',
    'hora'
  ],

  Productos: [
    'producto_id',
    'internal_code',
    'codigo_barras',
    'referencia',
    'nombre',
    'marca',
    'display_name',
    'categoria',
    'presentation',
    'foto_principal_url',
    'stock',
    'stock_minimo',
    'real_price',
    'precio_venta',
    'expiration_date',
    'estado',
    'created_at',
    'notes',
    'fecha',
    'hora'
  ],

  ProductoFotos: [
    'foto_id',
    'producto_id',
    'foto_url',
    'hash_visual',
    'es_principal',
    'creado',
    'fecha',
    'hora'
  ],

  StockMovimientos: [
    'movimiento_id',
    'producto_id',
    'tipo',
    'cantidad',
    'stock_anterior',
    'stock_nuevo',
    'fecha',
    'hora',
    'observacion'
  ],

  Ventas: [
    'venta_id',
    'fecha',
    'hora',
    'cliente_nombre',
    'cliente_whatsapp',
    'subtotal',
    'descuento',
    'total',
    'metodo_pago',
    'pdf_url',
    'estado'
  ],

  VentaDetalle: [
    'detalle_id',
    'venta_id',
    'producto',
    'marca',
    'cantidad',
    'precio_unitario',
    'total',
    'fecha',
    'hora'
  ],

  CreditosClientes: [
    'credito_cliente_id',
    'nombre',
    'whatsapp',
    'total_actual',
    'public_url',
    'estado',
    'fecha',
    'hora'
  ],

  CreditosDetalle: [
    'credito_detalle_id',
    'credito_cliente_id',
    'producto',
    'marca',
    'cantidad',
    'precio_unitario',
    'total',
    'fecha',
    'hora',
    'recogio',
    'observacion',
    'estado'
  ],

  CreditosPagos: [
    'pago_credito_id',
    'credito_cliente_id',
    'nombre_cliente',
    'fecha_pago',
    'fecha',
    'hora',
    'total_pagado',
    'detalle_json',
    'pdf_url',
    'estado'
  ],

  PagosQR: [
    'pago_id',
    'etiqueta',
    'metodo',
    'titular',
    'numero',
    'qr_url',
    'mensaje_pago',
    'estado',
    'fecha',
    'hora'
  ],

  Publicidad: [
    'publicidad_id',
    'titulo',
    'texto',
    'tipo_medio',
    'media_url',
    'ubicacion',
    'estilo',
    'color_fondo',
    'color_texto',
    'duracion_seg',
    'velocidad',
    'estado',
    'fecha',
    'hora'
  ],

  Logs: [
    'log_id',
    'cliente_id',
    'usuario',
    'accion',
    'detalle',
    'fecha',
    'hora'
  ]
};

function doGet(e) {
  return json({
    ok: true,
    name: 'Bodega Chebitas API Sheets',
    sheet: SHEET_ID,
    timezone: 'America/Lima',
    ahora: nowPeru()
  });
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');

    if (body.secret !== SECRET) {
      return json({
        ok: false,
        error: 'secret incorrecto'
      });
    }

    const tab = body.tab || 'Logs';
    const action = body.action || 'append';
    const key = body.key || 'id';
    const data = body.data || {};

    const stamp = nowPeru();

    if (!data.fecha) data.fecha = stamp.fecha;
    if (!data.hora) data.hora = stamp.hora;

    const sh = getSheet(tab);

    if (action === 'upsert') {
      upsert(sh, key, data);
    } else if (action === 'delete') {
      softDelete(sh, key, data[key], data);
    } else {
      append(sh, data);
    }

    return json({
      ok: true,
      tab: tab,
      action: action,
      fecha: stamp.fecha,
      hora: stamp.hora
    });

  } catch (err) {
    return json({
      ok: false,
      error: String(err)
    });
  }
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function nowPeru() {
  const now = new Date();

  return {
    fecha: Utilities.formatDate(now, 'America/Lima', 'dd/MM/yyyy'),
    hora: Utilities.formatDate(now, 'America/Lima', 'HH:mm:ss')
  };
}

function getSheet(name) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sh = ss.getSheetByName(name);

  if (!sh) {
    sh = ss.insertSheet(name);
  }

  const headersDefault = HEADERS[name] || HEADERS.Config;

  const lastCol = Math.max(1, sh.getLastColumn());
  const current = sh
    .getRange(1, 1, 1, lastCol)
    .getValues()[0]
    .filter(String);

  if (current.length === 0) {
    sh.getRange(1, 1, 1, headersDefault.length).setValues([headersDefault]);
    styleHeader(sh, headersDefault.length);
  } else {
    let changed = false;

    headersDefault.forEach(h => {
      if (current.indexOf(h) === -1) {
        current.push(h);
        changed = true;
      }
    });

    if (changed) {
      sh.getRange(1, 1, 1, current.length).setValues([current]);
      styleHeader(sh, current.length);
    }
  }

  return sh;
}

function headers(sh) {
  return sh
    .getRange(1, 1, 1, Math.max(1, sh.getLastColumn()))
    .getValues()[0]
    .filter(String);
}

function append(sh, data) {
  let h = headers(sh);
  h = ensureHeaders(sh, h, Object.keys(data));

  const row = h.map(k => {
    return data[k] !== undefined ? data[k] : '';
  });

  sh.appendRow(row);
}

function upsert(sh, key, data) {
  let h = headers(sh);
  h = ensureHeaders(sh, h, Object.keys(data).concat([key]));

  const idx = h.indexOf(key);
  const value = String(data[key] || '');

  if (!value) {
    append(sh, data);
    return;
  }

  const values = sh.getDataRange().getValues();
  let rowIndex = -1;

  for (let i = 1; i < values.length; i++) {
    if (String(values[i][idx]) === value) {
      rowIndex = i + 1;
      break;
    }
  }

  const row = h.map(k => {
    return data[k] !== undefined ? data[k] : '';
  });

  if (rowIndex > 0) {
    sh.getRange(rowIndex, 1, 1, h.length).setValues([row]);
  } else {
    sh.appendRow(row);
  }
}

function softDelete(sh, key, value, data) {
  data.estado = 'BORRADO';
  data[key] = value;
  upsert(sh, key, data);
}

function ensureHeaders(sh, h, keys) {
  let changed = false;

  keys.forEach(k => {
    if (k && h.indexOf(k) === -1) {
      h.push(k);
      changed = true;
    }
  });

  if (changed) {
    sh.getRange(1, 1, 1, h.length).setValues([h]);
    styleHeader(sh, h.length);
  }

  return h;
}

function styleHeader(sh, cols) {
  sh.getRange(1, 1, 1, cols)
    .setBackground('#052e16')
    .setFontColor('#d1fae5')
    .setFontWeight('bold');

  sh.setFrozenRows(1);
}

function setup() {
  Object.keys(HEADERS).forEach(name => getSheet(name));

  Logger.log('Bodega Chebitas: pestañas preparadas correctamente con hora Perú');
}

function testConexion() {
  const sh = getSheet('Logs');
  const stamp = nowPeru();

  append(sh, {
    log_id: 'TEST-' + new Date().getTime(),
    cliente_id: '',
    usuario: '',
    accion: 'PRUEBA',
    detalle: 'Conexión Apps Script funcionando correctamente',
    fecha: stamp.fecha,
    hora: stamp.hora
  });

  Logger.log('Prueba guardada correctamente en Logs con hora Perú');
}
