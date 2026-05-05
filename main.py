
import os
import io
import json
import uuid
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional, List

import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, ImageStat
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

# ============================
# CONFIGURACION
# ============================
APP_NAME = os.getenv('APP_NAME', 'Bodega Chebitas')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./bodetronic.db')
BASE_URL = os.getenv('BASE_URL', '').rstrip('/')
SUPPORT_WHATSAPP = os.getenv('SUPPORT_WHATSAPP', '51992657332')
SHEET_WEBAPP_URL = os.getenv('SHEET_WEBAPP_URL', '').strip()
SHEET_SECRET = os.getenv('SHEET_SECRET', 'chebitas-2026').strip()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', 'uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title='Bodega Chebitas Directo')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')

# ============================
# MODELOS SQLITE
# ============================
class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(120), unique=True, index=True)
    value = Column(Text, default='')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    internal_code = Column(String(80), index=True)
    barcode = Column(String(140), default='', index=True)
    reference = Column(String(160), default='', index=True)
    name = Column(String(200), index=True)
    brand = Column(String(160), default='')
    category = Column(String(120), default='Bodega')
    presentation = Column(String(120), default='')
    image_url = Column(Text, default='')
    visual_hash = Column(String(80), default='')
    stock = Column(Float, default=0)
    min_stock = Column(Float, default=1)
    real_price = Column(Float, default=0)
    sale_price = Column(Float, default=0)
    expiration_date = Column(String(40), default='')
    notes = Column(Text, default='')
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    images = relationship('ProductImage', back_populates='product', cascade='all, delete-orphan')

class ProductImage(Base):
    __tablename__ = 'product_images'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), index=True)
    image_url = Column(Text, default='')
    visual_hash = Column(String(80), default='')
    is_main = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    product = relationship('Product', back_populates='images')

class StockMovement(Base):
    __tablename__ = 'stock_movements'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), index=True)
    movement_type = Column(String(40), default='AJUSTE')
    quantity = Column(Float, default=0)
    old_stock = Column(Float, default=0)
    new_stock = Column(Float, default=0)
    notes = Column(Text, default='')
    created_at = Column(DateTime, server_default=func.now())

class PaymentMethod(Base):
    __tablename__ = 'payment_methods'
    id = Column(Integer, primary_key=True)
    label = Column(String(140), default='Pago principal')
    method = Column(String(80), default='Yape')
    holder_name = Column(String(160), default='')
    phone = Column(String(50), default='')
    qr_url = Column(Text, default='')
    message = Column(Text, default='')
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Advertisement(Base):
    __tablename__ = 'advertisements'
    id = Column(Integer, primary_key=True)
    title = Column(String(180), default='')
    text_body = Column(Text, default='')
    media_url = Column(Text, default='')
    media_type = Column(String(60), default='texto')
    location = Column(String(80), default='inicio')
    display_mode = Column(String(80), default='card')
    link_url = Column(Text, default='')
    bg_color = Column(String(40), default='#03120b')
    text_color = Column(String(40), default='#d9f99d')
    duration_seconds = Column(Integer, default=8)
    speed = Column(Integer, default=14)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    token = Column(String(80), unique=True, index=True)
    customer_name = Column(String(160), default='Cliente')
    customer_phone = Column(String(60), default='')
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_method = Column(String(80), default='Efectivo')
    status = Column(String(40), default='PAGADO')
    created_at = Column(DateTime, server_default=func.now())
    items = relationship('SaleItem', back_populates='sale', cascade='all, delete-orphan')

class SaleItem(Base):
    __tablename__ = 'sale_items'
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    product_name = Column(String(220), default='')
    brand = Column(String(160), default='')
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    total = Column(Float, default=0)
    sale = relationship('Sale', back_populates='items')

class CreditCustomer(Base):
    __tablename__ = 'credit_customers'
    id = Column(Integer, primary_key=True)
    public_token = Column(String(80), unique=True, index=True)
    name = Column(String(180), index=True)
    whatsapp = Column(String(60), default='')
    total_current = Column(Float, default=0)
    active = Column(Boolean, default=True)
    notes = Column(Text, default='')
    created_at = Column(DateTime, server_default=func.now())
    items = relationship('CreditItem', back_populates='customer', cascade='all, delete-orphan')

class CreditItem(Base):
    __tablename__ = 'credit_items'
    id = Column(Integer, primary_key=True)
    credit_customer_id = Column(Integer, ForeignKey('credit_customers.id'), index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    product_name = Column(String(220), default='')
    brand = Column(String(160), default='')
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    total = Column(Float, default=0)
    picked_by = Column(String(160), default='')
    notes = Column(Text, default='')
    status = Column(String(40), default='PENDIENTE')
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship('CreditCustomer', back_populates='items')

class CreditPayment(Base):
    __tablename__ = 'credit_payments'
    id = Column(Integer, primary_key=True)
    credit_customer_id = Column(Integer, ForeignKey('credit_customers.id'), index=True)
    public_token = Column(String(80), unique=True, index=True)
    customer_name = Column(String(180), default='')
    total_paid = Column(Float, default=0)
    detail_json = Column(Text, default='')
    created_at = Column(DateTime, server_default=func.now())

# ============================
# UTILIDADES
# ============================
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

LIMA_TZ = ZoneInfo('America/Lima')

def now_dt():
    return datetime.now(LIMA_TZ)

def now_parts():
    d = now_dt()
    return d.strftime('%d/%m/%Y'), d.strftime('%H:%M:%S')

def now_str():
    return now_dt().strftime('%d/%m/%Y %H:%M:%S')

def public_url(path: str) -> str:
    if BASE_URL:
        return BASE_URL + path
    return path

def money(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def clean_phone(phone: str) -> str:
    phone = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if phone and not phone.startswith('51'):
        phone = '51' + phone
    return phone

def product_title(p: Product) -> str:
    pieces = [p.name or '', p.brand or '', p.presentation or '']
    out = ' '.join([x.strip() for x in pieces if x and x.strip()])
    return out.strip() or 'Producto'

def product_dict(p: Product, include_images=True):
    d = {
        'id': p.id, 'internal_code': p.internal_code, 'barcode': p.barcode, 'reference': p.reference,
        'name': p.name, 'brand': p.brand, 'display_name': product_title(p), 'category': p.category,
        'presentation': p.presentation, 'image_url': p.image_url, 'stock': money(p.stock),
        'min_stock': money(p.min_stock), 'real_price': money(p.real_price), 'sale_price': money(p.sale_price),
        'expiration_date': p.expiration_date, 'notes': p.notes, 'active': p.active, 'created_at': str(p.created_at or '')
    }
    if include_images:
        d['images'] = [{'id': im.id, 'image_url': im.image_url, 'is_main': im.is_main, 'position': im.position} for im in sorted(p.images, key=lambda x: x.position)]
    return d

def setting_dict(db):
    values = {s.key: s.value for s in db.query(Setting).all()}
    defaults = {
        'business_name': 'Bodega Chebitas', 'subtitle': 'Inventario, ventas y créditos',
        'logo_text': 'B', 'primary_color': '#20ff29', 'bg_color': '#020806',
        'text_color': '#d6dde7', 'support_whatsapp': SUPPORT_WHATSAPP,
        'footer': 'AeroxLab | WEB DEVELOPER TEAM | © 2025-2026 Aerox Security Consulting LLC | Derechos reservados | Políticas de privacidad'
    }
    defaults.update(values)
    return defaults

def save_setting(db, key, value):
    s = db.query(Setting).filter(Setting.key == key).first()
    if not s:
        s = Setting(key=key, value=str(value or ''))
        db.add(s)
    else:
        s.value = str(value or '')
    db.commit()
    sheet_sync('Config', 'upsert', {'clave': key, 'valor': str(value or ''), 'actualizado': now_str()}, 'clave')
    return s

# ============================
# APPS SCRIPT SYNC
# ============================
def sheet_sync(tab: str, action: str, data: dict, key: str = 'id'):
    if not SHEET_WEBAPP_URL:
        return {'ok': False, 'skipped': True, 'reason': 'SHEET_WEBAPP_URL vacío'}
    data = dict(data or {})
    fecha, hora = now_parts()
    # Siempre enviamos fecha/hora Perú a Google Sheets para evitar desfases de zona horaria.
    # Si una fecha llega con hora mezclada, la normalizamos a fecha + hora separada.
    if not data.get('fecha') or ':' in str(data.get('fecha')):
        data['fecha'] = fecha
    if not data.get('hora'):
        data['hora'] = hora
    payload = {'secret': SHEET_SECRET, 'tab': tab, 'action': action, 'key': key, 'data': data}
    try:
        r = requests.post(SHEET_WEBAPP_URL, json=payload, timeout=8)
        return r.json() if 'application/json' in r.headers.get('content-type', '') else {'ok': r.ok, 'text': r.text[:200]}
    except Exception as e:
        print('[SHEET_SYNC_ERROR]', tab, action, e)
        return {'ok': False, 'error': str(e)}

def sync_product(p: Product):
    data = product_dict(p, include_images=False)
    data.update({'producto_id': p.id, 'codigo_barras': p.barcode, 'nombre': p.name, 'marca': p.brand,
                 'precio_venta': p.sale_price, 'foto_principal_url': p.image_url, 'estado': 'ACTIVO' if p.active else 'BORRADO'})
    sheet_sync('Productos', 'upsert', data, 'producto_id')

def sync_credit_total(c: CreditCustomer):
    sheet_sync('CreditosClientes', 'upsert', {
        'credito_cliente_id': c.id, 'nombre': c.name, 'whatsapp': c.whatsapp,
        'total_actual': c.total_current, 'public_url': public_url('/public/credit/' + c.public_token),
        'estado': 'ACTIVO' if c.active else 'BORRADO'
    }, 'credito_cliente_id')

def process_image_upload(upload: UploadFile, folder='products', make_white=True):
    suffix = Path(upload.filename or 'foto.jpg').suffix.lower() or '.jpg'
    raw = upload.file.read()
    if not raw:
        raise HTTPException(400, 'Imagen vacía')
    try:
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        img = ImageOps.exif_transpose(img)
        img.thumbnail((1200, 1200))
        if make_white:
            img = make_background_white(img)
        filename = f'{folder}_{uuid.uuid4().hex}.jpg'
        out = UPLOAD_DIR / filename
        img.save(out, 'JPEG', quality=90)
        return '/uploads/' + filename, image_hash(img)
    except Exception as e:
        raise HTTPException(400, f'No se pudo procesar imagen: {e}')

def make_background_white(img: Image.Image) -> Image.Image:
    """
    Limpieza automática para fotos de producto:
    - intenta detectar el fondo conectado a los bordes de la imagen;
    - convierte ese fondo a blanco;
    - deja la foto final sobre un lienzo cuadrado blanco.
    No es una IA pesada tipo rembg, pero funciona como limpieza rápida para bodega desde celular.
    """
    img = img.convert('RGB')
    w, h = img.size
    px = img.load()

    # 1) Tomar muestras de bordes para estimar el color del fondo.
    samples = []
    step = max(1, min(w, h) // 50)
    for x in range(0, w, step):
        samples.append(px[x, 0])
        samples.append(px[x, h - 1])
    for y in range(0, h, step):
        samples.append(px[0, y])
        samples.append(px[w - 1, y])

    if not samples:
        return img

    bg = tuple(sum(c[i] for c in samples) // len(samples) for i in range(3))

    def dist(c):
        return abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])

    # Umbral moderado para no borrar el producto por accidente.
    threshold = 92
    out = img.copy()
    op = out.load()

    # 2) Flood fill solo desde bordes: elimina fondo conectado, no borra detalles internos.
    from collections import deque
    q = deque()
    seen = bytearray(w * h)

    def push(x, y):
        if 0 <= x < w and 0 <= y < h:
            idx = y * w + x
            if not seen[idx]:
                seen[idx] = 1
                q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        c = px[x, y]
        # También limpia fondos muy claros aunque varíen un poco.
        is_bg = dist(c) <= threshold or (sum(c) > 705 and dist(c) <= 150)
        if is_bg:
            op[x, y] = (255, 255, 255)
            push(x + 1, y)
            push(x - 1, y)
            push(x, y + 1)
            push(x, y - 1)

    # 3) Suavizar sombras muy claras restantes hacia blanco.
    for y in range(h):
        for x in range(w):
            r, g, b = op[x, y]
            if (r + g + b) > 735:
                op[x, y] = (255, 255, 255)

    # 4) Lienzo cuadrado blanco para que quede ordenado como foto de producto.
    side = max(out.size)
    canvas_img = Image.new('RGB', (side, side), 'white')
    canvas_img.paste(out, ((side - out.size[0]) // 2, (side - out.size[1]) // 2))
    return canvas_img

def image_hash(img: Image.Image):
    img = img.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
    vals = list(img.getdata())
    avg = sum(vals) / len(vals)
    bits = ''.join('1' if v > avg else '0' for v in vals)
    return hex(int(bits, 2))[2:].zfill(16)

def hamming(a, b):
    try:
        return bin(int(a, 16) ^ int(b, 16)).count('1')
    except Exception:
        return 64

def recalc_credit(db, c: CreditCustomer):
    total = sum(i.total for i in c.items if i.status == 'PENDIENTE')
    c.total_current = money(total)
    db.commit()
    db.refresh(c)
    sync_credit_total(c)
    return c.total_current

# ============================
# INIT
# ============================
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        defaults = {
            'business_name': 'Bodega Chebitas', 'subtitle': 'Inventario, ventas y créditos',
            'logo_text': 'B', 'primary_color': '#20ff29', 'bg_color': '#020806',
            'text_color': '#d6dde7', 'support_whatsapp': SUPPORT_WHATSAPP,
            'footer': 'AeroxLab | WEB DEVELOPER TEAM | © 2025-2026 Aerox Security Consulting LLC | Derechos reservados | Políticas de privacidad'
        }
        for k,v in defaults.items():
            if not db.query(Setting).filter(Setting.key==k).first():
                db.add(Setting(key=k, value=v))
        db.commit()
    finally:
        db.close()

@app.on_event('startup')
def startup():
    init_db()

# ============================
# RUTAS HTML
# ============================
@app.get('/', response_class=HTMLResponse)
def index():
    return FileResponse('static/index.html')

@app.get('/admin', response_class=HTMLResponse)
def no_admin():
    return FileResponse('static/index.html')

# ============================
# API GENERAL
# ============================
@app.get('/api/state')
def get_state():
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.active == True).order_by(Product.id.desc()).all()
        credits = db.query(CreditCustomer).filter(CreditCustomer.active == True).order_by(CreditCustomer.id.desc()).all()
        payments = db.query(PaymentMethod).filter(PaymentMethod.active == True).order_by(PaymentMethod.id.desc()).all()
        ads = db.query(Advertisement).filter(Advertisement.active == True).order_by(Advertisement.id.desc()).all()
        sales_count = db.query(Sale).count()
        return {
            'settings': setting_dict(db),
            'summary': {'products': len(products), 'credits': len(credits), 'sales': sales_count, 'stock_low': len([p for p in products if p.stock <= p.min_stock])},
            'products': [product_dict(p) for p in products],
            'credits': [{'id': c.id, 'name': c.name, 'whatsapp': c.whatsapp, 'total_current': money(c.total_current), 'public_url': public_url('/public/credit/' + c.public_token)} for c in credits],
            'payments': [{'id': p.id, 'label': p.label, 'method': p.method, 'holder_name': p.holder_name, 'phone': p.phone, 'qr_url': p.qr_url, 'message': p.message} for p in payments],
            'ads': [{'id': a.id, 'title': a.title, 'text_body': a.text_body, 'media_url': a.media_url, 'media_type': a.media_type, 'location': a.location, 'display_mode': a.display_mode, 'bg_color': a.bg_color, 'text_color': a.text_color, 'duration_seconds': a.duration_seconds, 'speed': a.speed, 'link_url': a.link_url} for a in ads]
        }
    finally:
        db.close()

@app.post('/api/upload')
def upload_file(file: UploadFile = File(...), folder: str = Form('general')):
    suffix = Path(file.filename or 'archivo.bin').suffix.lower()
    fname = f'{folder}_{uuid.uuid4().hex}{suffix}'
    out = UPLOAD_DIR / fname
    with open(out, 'wb') as f:
        f.write(file.file.read())
    return {'ok': True, 'url': '/uploads/' + fname}

# ============================
# PRODUCTOS
# ============================
@app.post('/api/products')
def create_product(
    name: str = Form(...), brand: str = Form(''), category: str = Form('Bodega'), presentation: str = Form(''),
    barcode: str = Form(''), reference: str = Form(''), stock: float = Form(0), min_stock: float = Form(1),
    real_price: float = Form(0), sale_price: float = Form(0), expiration_date: str = Form(''), notes: str = Form(''),
    photos: Optional[List[UploadFile]] = File(None)
):
    db = SessionLocal()
    try:
        internal = 'BOD-' + uuid.uuid4().hex[:6].upper()
        p = Product(name=name.strip(), brand=brand.strip(), category=category, presentation=presentation.strip(), barcode=barcode.strip(), reference=reference.strip(), stock=stock, min_stock=min_stock, real_price=real_price, sale_price=sale_price, expiration_date=expiration_date, notes=notes, internal_code=internal)
        db.add(p); db.commit(); db.refresh(p)
        if photos:
            for idx, photo in enumerate(photos):
                if photo and photo.filename:
                    url, vh = process_image_upload(photo, 'product', True)
                    im = ProductImage(product_id=p.id, image_url=url, visual_hash=vh, is_main=(idx == 0), position=idx)
                    db.add(im)
                    if idx == 0:
                        p.image_url = url; p.visual_hash = vh
            db.commit(); db.refresh(p)
        sync_product(p)
        for im in p.images:
            sheet_sync('ProductoFotos', 'upsert', {'foto_id': im.id, 'producto_id': p.id, 'foto_url': im.image_url, 'hash_visual': im.visual_hash, 'es_principal': str(im.is_main)}, 'foto_id')
        return {'ok': True, 'product': product_dict(p)}
    finally:
        db.close()

@app.put('/api/products/{product_id}')
def update_product(product_id: int, payload: dict):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p or not p.active: raise HTTPException(404, 'Producto no encontrado')
        for field in ['name','brand','category','presentation','barcode','reference','expiration_date','notes']:
            if field in payload: setattr(p, field, str(payload.get(field) or ''))
        for field in ['stock','min_stock','real_price','sale_price']:
            if field in payload: setattr(p, field, money(payload.get(field)))
        db.commit(); db.refresh(p); sync_product(p)
        return {'ok': True, 'product': product_dict(p)}
    finally:
        db.close()

@app.delete('/api/products/{product_id}')
def delete_product(product_id: int):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p: raise HTTPException(404, 'Producto no encontrado')
        p.active = False; db.commit(); sync_product(p)
        return {'ok': True}
    finally:
        db.close()

@app.post('/api/products/{product_id}/photos')
def add_product_photos(product_id: int, photos: List[UploadFile] = File(...)):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p: raise HTTPException(404, 'Producto no encontrado')
        base_pos = db.query(ProductImage).filter(ProductImage.product_id == p.id).count()
        added = []
        for idx, photo in enumerate(photos):
            url, vh = process_image_upload(photo, 'product', True)
            is_main = (base_pos == 0 and idx == 0)
            im = ProductImage(product_id=p.id, image_url=url, visual_hash=vh, is_main=is_main, position=base_pos+idx)
            db.add(im); db.commit(); db.refresh(im)
            if is_main:
                p.image_url = url; p.visual_hash = vh; db.commit()
            added.append({'id': im.id, 'image_url': im.image_url})
            sheet_sync('ProductoFotos', 'upsert', {'foto_id': im.id, 'producto_id': p.id, 'foto_url': im.image_url, 'hash_visual': im.visual_hash, 'es_principal': str(im.is_main)}, 'foto_id')
        sync_product(p)
        return {'ok': True, 'photos': added}
    finally:
        db.close()


@app.post('/api/products/{product_id}/photos/{photo_id}/main')
def set_product_main_photo(product_id: int, photo_id: int):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p: raise HTTPException(404, 'Producto no encontrado')
        target = db.query(ProductImage).filter(ProductImage.product_id == product_id, ProductImage.id == photo_id).first()
        if not target: raise HTTPException(404, 'Foto no encontrada')
        for im in db.query(ProductImage).filter(ProductImage.product_id == product_id).all():
            im.is_main = (im.id == photo_id)
        p.image_url = target.image_url
        p.visual_hash = target.visual_hash
        db.commit(); db.refresh(p); sync_product(p)
        return {'ok': True, 'product': product_dict(p)}
    finally:
        db.close()

@app.delete('/api/products/{product_id}/photos/{photo_id}')
def delete_product_photo(product_id: int, photo_id: int):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p: raise HTTPException(404, 'Producto no encontrado')
        im = db.query(ProductImage).filter(ProductImage.product_id == product_id, ProductImage.id == photo_id).first()
        if not im: raise HTTPException(404, 'Foto no encontrada')
        was_main = im.is_main
        db.delete(im)
        db.commit()
        if was_main:
            first = db.query(ProductImage).filter(ProductImage.product_id == product_id).order_by(ProductImage.position.asc(), ProductImage.id.asc()).first()
            if first:
                first.is_main = True
                p.image_url = first.image_url
                p.visual_hash = first.visual_hash
            else:
                p.image_url = ''
                p.visual_hash = ''
            db.commit()
        sync_product(p)
        return {'ok': True}
    finally:
        db.close()

@app.get('/api/products/search')
def search_products(q: str = ''):
    db = SessionLocal()
    try:
        ql = (q or '').strip().lower()
        products = db.query(Product).filter(Product.active == True).all()
        if ql:
            products = [p for p in products if ql in (p.name or '').lower() or ql in (p.brand or '').lower() or ql in (p.barcode or '').lower() or ql in (p.internal_code or '').lower() or ql in (p.reference or '').lower()]
        return {'ok': True, 'products': [product_dict(p) for p in products[:50]]}
    finally:
        db.close()

@app.post('/api/products/{product_id}/stock')
def update_stock(product_id: int, payload: dict):
    db = SessionLocal()
    try:
        p = db.query(Product).get(product_id)
        if not p: raise HTTPException(404, 'Producto no encontrado')
        qty = money(payload.get('quantity'))
        typ = str(payload.get('type') or 'CARGA').upper()
        old = money(p.stock)
        if typ == 'DESCARGA': p.stock = old - qty
        elif typ == 'AJUSTE': p.stock = qty
        else: p.stock = old + qty
        p.stock = max(0, money(p.stock))
        mv = StockMovement(product_id=p.id, movement_type=typ, quantity=qty, old_stock=old, new_stock=p.stock, notes=str(payload.get('notes') or ''))
        db.add(mv); db.commit(); db.refresh(mv); sync_product(p)
        sheet_sync('StockMovimientos', 'upsert', {'movimiento_id': mv.id, 'producto_id': p.id, 'tipo': typ, 'cantidad': qty, 'stock_anterior': old, 'stock_nuevo': p.stock, 'fecha': now_str()}, 'movimiento_id')
        return {'ok': True, 'product': product_dict(p)}
    finally:
        db.close()

# ============================
# SCANNER / IMAGEN
# ============================
@app.post('/api/scan-image')
def scan_image(file: UploadFile = File(...)):
    url, vh = process_image_upload(file, 'scan', True)
    db = SessionLocal()
    try:
        imgs = db.query(ProductImage).all()
        best = None; best_dist = 65
        for im in imgs:
            d = hamming(vh, im.visual_hash)
            if d < best_dist:
                best_dist = d; best = im
        if best and best.product and best_dist <= 22 and best.product.active:
            score = round(max(0, 100 - best_dist * 4.2), 1)
            return {'ok': True, 'match': True, 'score': score, 'captured_url': url, 'product': product_dict(best.product)}
        return {'ok': True, 'match': False, 'captured_url': url, 'message': 'No hay coincidencia con productos registrados'}
    finally:
        db.close()

# ============================
# PAGOS QR
# ============================
@app.post('/api/payments')
def create_payment(label: str = Form('Pago principal'), method: str = Form('Yape'), holder_name: str = Form(''), phone: str = Form(''), message: str = Form(''), qr: Optional[UploadFile] = File(None)):
    db = SessionLocal()
    try:
        qr_url = ''
        if qr and qr.filename:
            qr_url, _ = process_image_upload(qr, 'qr', False)
        p = PaymentMethod(label=label, method=method, holder_name=holder_name, phone=phone, message=message, qr_url=qr_url)
        db.add(p); db.commit(); db.refresh(p)
        sheet_sync('PagosQR', 'upsert', {'pago_id': p.id, 'etiqueta': p.label, 'metodo': p.method, 'titular': p.holder_name, 'numero': p.phone, 'qr_url': p.qr_url, 'mensaje_pago': p.message, 'estado': 'ACTIVO'}, 'pago_id')
        return {'ok': True, 'payment': {'id': p.id, 'label': p.label, 'method': p.method, 'holder_name': p.holder_name, 'phone': p.phone, 'qr_url': p.qr_url, 'message': p.message}}
    finally:
        db.close()


@app.put('/api/payments/{payment_id}')
def update_payment(payment_id: int, payload: dict):
    db = SessionLocal()
    try:
        p = db.query(PaymentMethod).get(payment_id)
        if not p: raise HTTPException(404, 'Pago no encontrado')
        for field in ['label','method','holder_name','phone','message']:
            if field in payload:
                setattr(p, field, str(payload.get(field) or ''))
        db.commit()
        sheet_sync('PagosQR', 'upsert', {'pago_id': p.id, 'etiqueta': p.label, 'metodo': p.method, 'titular': p.holder_name, 'numero': p.phone, 'qr_url': p.qr_url, 'mensaje_pago': p.message, 'estado': 'ACTIVO'}, 'pago_id')
        return {'ok': True}
    finally:
        db.close()

@app.delete('/api/payments/{payment_id}')
def delete_payment(payment_id: int):
    db = SessionLocal()
    try:
        p = db.query(PaymentMethod).get(payment_id)
        if p:
            p.active = False; db.commit()
            sheet_sync('PagosQR', 'upsert', {'pago_id': p.id, 'estado': 'BORRADO'}, 'pago_id')
        return {'ok': True}
    finally:
        db.close()

# ============================
# PUBLICIDAD
# ============================
@app.post('/api/ads')
def create_ad(title: str = Form(''), text_body: str = Form(''), media_type: str = Form('texto'), location: str = Form('inicio'), display_mode: str = Form('card'), link_url: str = Form(''), bg_color: str = Form('#03120b'), text_color: str = Form('#d9f99d'), duration_seconds: int = Form(8), speed: int = Form(14), media: Optional[UploadFile] = File(None)):
    db = SessionLocal()
    try:
        media_url = ''
        if media and media.filename:
            up = upload_file(media, 'ads')
            media_url = up['url']
        a = Advertisement(title=title, text_body=text_body, media_type=media_type, location=location, display_mode=display_mode, link_url=link_url, bg_color=bg_color, text_color=text_color, duration_seconds=duration_seconds, speed=speed, media_url=media_url)
        db.add(a); db.commit(); db.refresh(a)
        sheet_sync('Publicidad', 'upsert', {'publicidad_id': a.id, 'titulo': a.title, 'texto': a.text_body, 'tipo_medio': a.media_type, 'media_url': a.media_url, 'ubicacion': a.location, 'estilo': a.display_mode, 'estado': 'ACTIVO'}, 'publicidad_id')
        return {'ok': True, 'ad': {'id': a.id}}
    finally:
        db.close()

@app.delete('/api/ads/{ad_id}')
def delete_ad(ad_id: int):
    db = SessionLocal()
    try:
        a = db.query(Advertisement).get(ad_id)
        if a:
            a.active = False; db.commit(); sheet_sync('Publicidad', 'upsert', {'publicidad_id': a.id, 'estado': 'BORRADO'}, 'publicidad_id')
        return {'ok': True}
    finally:
        db.close()

# ============================
# CONFIGURACION
# ============================
@app.post('/api/settings')
def update_settings(payload: dict):
    db = SessionLocal()
    try:
        for k,v in payload.items(): save_setting(db, k, v)
        return {'ok': True, 'settings': setting_dict(db)}
    finally:
        db.close()

# ============================
# VENTAS POS
# ============================
@app.post('/api/sales')
def create_sale(payload: dict):
    db = SessionLocal()
    try:
        items = payload.get('items') or []
        if not items: raise HTTPException(400, 'Carrito vacío')
        sale = Sale(token=uuid.uuid4().hex, customer_name=payload.get('customer_name') or 'Cliente', customer_phone=clean_phone(payload.get('customer_phone') or ''), payment_method=payload.get('payment_method') or 'Efectivo')
        db.add(sale); db.commit(); db.refresh(sale)
        total = 0
        for it in items:
            p = db.query(Product).get(int(it.get('product_id')))
            qty = money(it.get('quantity') or 1)
            price = money(it.get('unit_price') if it.get('unit_price') is not None else (p.sale_price if p else 0))
            line_total = money(qty * price)
            total += line_total
            si = SaleItem(sale_id=sale.id, product_id=p.id if p else None, product_name=product_title(p) if p else it.get('product_name','Producto'), brand=p.brand if p else '', quantity=qty, unit_price=price, total=line_total)
            db.add(si)
            if p:
                old = p.stock; p.stock = max(0, money(p.stock - qty))
                db.add(StockMovement(product_id=p.id, movement_type='VENTA', quantity=qty, old_stock=old, new_stock=p.stock, notes='POS'))
                sync_product(p)
        sale.subtotal = money(total); sale.discount = money(payload.get('discount') or 0); sale.total = money(total - sale.discount)
        db.commit(); db.refresh(sale)
        sheet_sync('Ventas', 'upsert', {'venta_id': sale.id, 'fecha': now_str(), 'cliente_nombre': sale.customer_name, 'cliente_whatsapp': sale.customer_phone, 'total': sale.total, 'metodo_pago': sale.payment_method, 'pdf_url': public_url('/api/sales/'+sale.token+'/pdf'), 'estado': sale.status}, 'venta_id')
        for item in sale.items:
            sheet_sync('VentaDetalle', 'upsert', {'detalle_id': item.id, 'venta_id': sale.id, 'producto': item.product_name, 'marca': item.brand, 'cantidad': item.quantity, 'precio_unitario': item.unit_price, 'total': item.total}, 'detalle_id')
        msg = f'Hola, le envío su ticket de compra de {setting_dict(db).get("business_name","Bodega Chebitas")} por S/ {sale.total:.2f}. PDF: {public_url("/api/sales/"+sale.token+"/pdf")}'
        wa = f'https://wa.me/{sale.customer_phone}?text=' + requests.utils.quote(msg) if sale.customer_phone else ''
        return {'ok': True, 'sale_id': sale.id, 'total': sale.total, 'pdf_url': public_url('/api/sales/'+sale.token+'/pdf'), 'whatsapp_url': wa}
    finally:
        db.close()

@app.get('/api/sales/{token}/pdf')
def sale_pdf(token: str):
    db = SessionLocal()
    try:
        sale = db.query(Sale).filter(Sale.token == token).first()
        if not sale: raise HTTPException(404, 'Venta no encontrada')
        return make_sale_pdf(db, sale)
    finally:
        db.close()

# ============================
# CREDITOS
# ============================
@app.post('/api/credits/customers')
def create_credit_customer(payload: dict):
    db = SessionLocal()
    try:
        c = CreditCustomer(public_token=uuid.uuid4().hex, name=payload.get('name') or 'Cliente', whatsapp=clean_phone(payload.get('whatsapp') or ''), notes=payload.get('notes') or '')
        db.add(c); db.commit(); db.refresh(c); sync_credit_total(c)
        return {'ok': True, 'customer': {'id': c.id, 'name': c.name, 'whatsapp': c.whatsapp, 'total_current': c.total_current, 'public_url': public_url('/public/credit/'+c.public_token)}}
    finally:
        db.close()

@app.get('/api/credits/customers/{cid}')
def get_credit_customer(cid: int):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).get(cid)
        if not c: raise HTTPException(404, 'Cuenta no encontrada')
        return credit_customer_full(db, c)
    finally:
        db.close()

@app.delete('/api/credits/customers/{cid}')
def delete_credit_customer(cid: int):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).get(cid)
        if c:
            c.active = False; db.commit(); sync_credit_total(c)
        return {'ok': True}
    finally:
        db.close()

@app.post('/api/credits/customers/{cid}/items')
def add_credit_item(cid: int, payload: dict):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).get(cid)
        if not c: raise HTTPException(404, 'Cuenta no encontrada')
        product_id = payload.get('product_id')
        p = db.query(Product).get(int(product_id)) if product_id else None
        qty = money(payload.get('quantity') or 1)
        unit = money(payload.get('unit_price') if payload.get('unit_price') is not None else (p.sale_price if p else 0))
        ci = CreditItem(credit_customer_id=c.id, product_id=p.id if p else None, product_name=product_title(p) if p else payload.get('product_name','Producto'), brand=p.brand if p else payload.get('brand',''), quantity=qty, unit_price=unit, total=money(qty*unit), picked_by=payload.get('picked_by') or '', notes=payload.get('notes') or '')
        db.add(ci)
        if p and payload.get('discount_stock', True):
            old = p.stock; p.stock = max(0, money(p.stock-qty)); sync_product(p)
            db.add(StockMovement(product_id=p.id, movement_type='CREDITO', quantity=qty, old_stock=old, new_stock=p.stock, notes='Fiado'))
        db.commit(); db.refresh(ci); recalc_credit(db, c)
        sheet_sync('CreditosDetalle', 'upsert', {'credito_detalle_id': ci.id, 'credito_cliente_id': c.id, 'producto': ci.product_name, 'marca': ci.brand, 'cantidad': ci.quantity, 'precio_unitario': ci.unit_price, 'total': ci.total, 'fecha': now_str(), 'estado': ci.status}, 'credito_detalle_id')
        return {'ok': True, 'customer': credit_customer_full(db, c)}
    finally:
        db.close()

@app.put('/api/credits/items/{item_id}')
def update_credit_item(item_id: int, payload: dict):
    db = SessionLocal()
    try:
        ci = db.query(CreditItem).get(item_id)
        if not ci: raise HTTPException(404, 'Item no encontrado')
        for f in ['product_name','brand','picked_by','notes']:
            if f in payload: setattr(ci, f, str(payload.get(f) or ''))
        if 'quantity' in payload: ci.quantity = money(payload.get('quantity'))
        if 'unit_price' in payload: ci.unit_price = money(payload.get('unit_price'))
        ci.total = money(ci.quantity * ci.unit_price)
        db.commit(); recalc_credit(db, ci.customer)
        sheet_sync('CreditosDetalle', 'upsert', {'credito_detalle_id': ci.id, 'producto': ci.product_name, 'marca': ci.brand, 'cantidad': ci.quantity, 'precio_unitario': ci.unit_price, 'total': ci.total, 'estado': ci.status}, 'credito_detalle_id')
        return {'ok': True, 'customer': credit_customer_full(db, ci.customer)}
    finally:
        db.close()

@app.delete('/api/credits/items/{item_id}')
def delete_credit_item(item_id: int):
    db = SessionLocal()
    try:
        ci = db.query(CreditItem).get(item_id)
        if ci:
            c = ci.customer; ci.status = 'BORRADO'; db.commit(); recalc_credit(db, c)
            sheet_sync('CreditosDetalle', 'upsert', {'credito_detalle_id': ci.id, 'estado': 'BORRADO'}, 'credito_detalle_id')
        return {'ok': True}
    finally:
        db.close()

@app.post('/api/credits/customers/{cid}/paid')
def mark_credit_paid(cid: int):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).get(cid)
        if not c: raise HTTPException(404, 'Cuenta no encontrada')
        detail = [{'producto': i.product_name, 'marca': i.brand, 'cantidad': i.quantity, 'precio': i.unit_price, 'total': i.total} for i in c.items if i.status == 'PENDIENTE']
        total = money(sum(i['total'] for i in detail))
        pay = CreditPayment(credit_customer_id=c.id, public_token=uuid.uuid4().hex, customer_name=c.name, total_paid=total, detail_json=json.dumps(detail, ensure_ascii=False))
        db.add(pay)
        for i in c.items:
            if i.status == 'PENDIENTE': i.status = 'PAGADO'
        c.total_current = 0
        db.commit(); db.refresh(pay); sync_credit_total(c)
        sheet_sync('CreditosPagos', 'upsert', {'pago_credito_id': pay.id, 'credito_cliente_id': c.id, 'nombre_cliente': c.name, 'total_pagado': total, 'detalle_json': pay.detail_json, 'pdf_url': public_url('/public/credit-paid/'+pay.public_token+'/pdf'), 'estado': 'PAGADO'}, 'pago_credito_id')
        return {'ok': True, 'paid_pdf_url': public_url('/public/credit-paid/'+pay.public_token+'/pdf'), 'customer': credit_customer_full(db, c)}
    finally:
        db.close()

@app.get('/public/credit/{token}')
def public_credit(token: str):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).filter(CreditCustomer.public_token == token).first()
        if not c: raise HTTPException(404, 'No encontrado')
        return HTMLResponse(public_credit_html(db, c))
    finally:
        db.close()

@app.get('/public/credit/{token}/pdf')
def credit_pdf(token: str):
    db = SessionLocal()
    try:
        c = db.query(CreditCustomer).filter(CreditCustomer.public_token == token).first()
        if not c: raise HTTPException(404, 'No encontrado')
        return make_credit_pdf(db, c)
    finally:
        db.close()


@app.get('/public/credit-paid/{token}/pdf')
def credit_paid_pdf(token: str):
    db = SessionLocal()
    try:
        pay = db.query(CreditPayment).filter(CreditPayment.public_token == token).first()
        if not pay: raise HTTPException(404, 'No encontrado')
        return make_credit_payment_pdf(db, pay)
    finally:
        db.close()

def credit_customer_full(db, c: CreditCustomer):
    items = [i for i in c.items if i.status == 'PENDIENTE']
    paid = db.query(CreditPayment).filter(CreditPayment.credit_customer_id == c.id).order_by(CreditPayment.id.desc()).all()
    return {'ok': True, 'customer': {'id': c.id, 'name': c.name, 'whatsapp': c.whatsapp, 'total_current': money(c.total_current), 'public_url': public_url('/public/credit/'+c.public_token), 'pdf_url': public_url('/public/credit/'+c.public_token+'/pdf'), 'items': [{'id': i.id, 'product_id': i.product_id, 'product_name': i.product_name, 'brand': i.brand, 'quantity': i.quantity, 'unit_price': i.unit_price, 'total': i.total, 'picked_by': i.picked_by, 'notes': i.notes, 'created_at': str(i.created_at or '')} for i in items], 'paid_history': [{'id': p.id, 'total_paid': p.total_paid, 'created_at': str(p.created_at or ''), 'pdf_url': public_url('/public/credit-paid/'+p.public_token+'/pdf')} for p in paid]}}

def pdf_footer(pdf, s, w):
    footer = s.get('footer', 'AeroxLab | WEB DEVELOPER TEAM | © 2025-2026 Aerox Security Consulting LLC | Derechos reservados | Políticas de privacidad')
    pdf.setStrokeColorRGB(0.10, 0.36, 0.16)
    pdf.line(40, 42, w-40, 42)
    pdf.setFillColorRGB(0.58, 0.65, 0.60)
    pdf.setFont('Helvetica', 8)
    pdf.drawCentredString(w/2, 28, footer[:140])

def draw_pdf_header(pdf, s, w, y, subtitle):
    pdf.setFillColorRGB(0.02,0.08,0.04)
    pdf.roundRect(35, y-55, w-70, 55, 14, fill=1, stroke=0)
    pdf.setFillColorRGB(0.1,1,0.2)
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(55, y-25, s.get('business_name', 'Bodega Chebitas'))
    pdf.setFillColorRGB(0.85,0.9,0.86)
    pdf.setFont('Helvetica', 10)
    pdf.drawString(55, y-42, subtitle)

def make_sale_pdf(db, sale: Sale):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4); w,h = A4
    s = setting_dict(db); y = h-60
    draw_pdf_header(c, s, w, y, 'Ticket de venta')
    y-=90; c.setFillColorRGB(0,0,0); c.setFont('Helvetica',10)
    c.drawString(45,y,f'Cliente: {sale.customer_name}')
    c.drawString(260,y,f'WhatsApp: {sale.customer_phone or "-"}')
    c.drawRightString(w-45, y, f'Fecha: {str(sale.created_at or now_str())[:19]}')
    y-=28; c.setFont('Helvetica-Bold',10)
    c.drawString(45,y,'Producto'); c.drawString(270,y,'Cant.'); c.drawString(340,y,'P.Unit'); c.drawString(430,y,'Total'); y-=18
    c.setFont('Helvetica',9)
    for it in sale.items:
        c.drawString(45,y,(it.product_name or '')[:34])
        c.drawRightString(310,y,str(it.quantity))
        c.drawRightString(390,y,f'S/ {it.unit_price:.2f}')
        c.drawRightString(500,y,f'S/ {it.total:.2f}')
        y-=18
        if y<90:
            pdf_footer(c, s, w)
            c.showPage(); y=h-60; draw_pdf_header(c, s, w, y, 'Ticket de venta'); y-=90; c.setFillColorRGB(0,0,0); c.setFont('Helvetica',9)
    y-=14; c.setFont('Helvetica-Bold',16); c.drawRightString(500,y,f'TOTAL S/ {sale.total:.2f}')
    pdf_footer(c, s, w)
    c.save(); buf.seek(0)
    return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename=ticket_venta_{sale.id}.pdf'})

def make_credit_pdf(db, cst: CreditCustomer):
    buf = io.BytesIO(); pdf = canvas.Canvas(buf, pagesize=A4); w,h = A4
    s = setting_dict(db); y = h-60
    draw_pdf_header(pdf, s, w, y, 'Detalle de crédito / fiado')
    y-=90; pdf.setFillColorRGB(0,0,0); pdf.setFont('Helvetica-Bold',14); pdf.drawString(45,y,cst.name)
    pdf.setFont('Helvetica',10); pdf.drawRightString(w-45, y, f'Fecha: {now_str()}'); y-=18
    pdf.drawString(45,y, f'WhatsApp: {cst.whatsapp or "-"}'); y-=22
    pdf.setFont('Helvetica-Bold',10); pdf.drawString(45,y,'Producto'); pdf.drawString(245,y,'Marca'); pdf.drawString(325,y,'Cant.'); pdf.drawString(395,y,'P.Unit'); pdf.drawString(475,y,'Total'); y-=18
    pdf.setFont('Helvetica',9)
    for it in cst.items:
        if it.status != 'PENDIENTE':
            continue
        pdf.drawString(45,y,(it.product_name or '')[:30])
        pdf.drawString(245,y,(it.brand or '')[:14])
        pdf.drawRightString(360,y,str(it.quantity))
        pdf.drawRightString(445,y,f'S/ {it.unit_price:.2f}')
        pdf.drawRightString(525,y,f'S/ {it.total:.2f}')
        y-=18
        if y < 90:
            pdf_footer(pdf, s, w)
            pdf.showPage(); y=h-60; draw_pdf_header(pdf, s, w, y, 'Detalle de crédito / fiado'); y-=90; pdf.setFillColorRGB(0,0,0); pdf.setFont('Helvetica',9)
    y-=14; pdf.setFont('Helvetica-Bold',16); pdf.drawRightString(525,y,f'TOTAL PENDIENTE S/ {cst.total_current:.2f}')
    y-=22; pdf.setFont('Helvetica',10); pdf.drawString(45,y, 'Documento de solo lectura para el cliente.')
    pdf_footer(pdf, s, w)
    pdf.save(); buf.seek(0)
    safe_name = ''.join(ch if ch.isalnum() else '_' for ch in cst.name or 'cliente')
    return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename=credito_{safe_name}.pdf'})

def make_credit_payment_pdf(db, pay: CreditPayment):
    buf = io.BytesIO(); pdf = canvas.Canvas(buf, pagesize=A4); w,h = A4
    s = setting_dict(db); y = h-60
    draw_pdf_header(pdf, s, w, y, 'Crédito marcado como pagado')
    detail = json.loads(pay.detail_json or '[]')
    y-=90; pdf.setFillColorRGB(0,0,0); pdf.setFont('Helvetica-Bold',14); pdf.drawString(45,y,pay.customer_name)
    pdf.setFont('Helvetica',10); pdf.drawRightString(w-45, y, f'Fecha: {str(pay.created_at or now_str())[:19]}'); y-=28
    pdf.setFont('Helvetica-Bold',10); pdf.drawString(45,y,'Producto'); pdf.drawString(245,y,'Marca'); pdf.drawString(325,y,'Cant.'); pdf.drawString(395,y,'P.Unit'); pdf.drawString(475,y,'Total'); y-=18
    pdf.setFont('Helvetica',9)
    for it in detail:
        pdf.drawString(45,y,str(it.get('product_name',''))[:30])
        pdf.drawString(245,y,str(it.get('brand',''))[:14])
        pdf.drawRightString(360,y,str(it.get('quantity',1)))
        pdf.drawRightString(445,y,f"S/ {money(it.get('unit_price')):.2f}")
        pdf.drawRightString(525,y,f"S/ {money(it.get('total')):.2f}")
        y-=18
        if y < 90:
            pdf_footer(pdf, s, w)
            pdf.showPage(); y=h-60; draw_pdf_header(pdf, s, w, y, 'Crédito marcado como pagado'); y-=90; pdf.setFillColorRGB(0,0,0); pdf.setFont('Helvetica',9)
    y-=14; pdf.setFont('Helvetica-Bold',16); pdf.drawRightString(525,y,f'TOTAL PAGADO S/ {pay.total_paid:.2f}')
    y-=22; pdf.setFont('Helvetica-Bold',12); pdf.drawString(45,y,'ESTADO: PAGADO')
    pdf_footer(pdf, s, w)
    pdf.save(); buf.seek(0)
    safe_name = ''.join(ch if ch.isalnum() else '_' for ch in pay.customer_name or 'cliente')
    return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename=credito_pagado_{safe_name}.pdf'})

def public_credit_html(db, cst: CreditCustomer):
    rows = ''.join(f'<tr><td>{i.product_name} {i.brand}</td><td>{i.quantity}</td><td>S/ {i.unit_price:.2f}</td><td>S/ {i.total:.2f}</td></tr>' for i in cst.items if i.status == 'PENDIENTE')
    s = setting_dict(db)
    footer = s.get('footer', 'AeroxLab | WEB DEVELOPER TEAM | © 2025-2026 Aerox Security Consulting LLC | Derechos reservados | Políticas de privacidad')
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Crédito {cst.name}</title><style>body{{font-family:Arial;background:#020806;color:#e5e7eb;padding:20px}}.card{{max-width:860px;margin:auto;border:1px solid #0a5;border-radius:24px;padding:22px;background:#06120d}}h1{{color:#20ff29;margin:0}}h2{{margin:10px 0 8px}}.note{{background:#07140d;border:1px solid #15481f;padding:12px 14px;border-radius:14px;color:#b8c5bd}}table{{width:100%;border-collapse:collapse;margin-top:14px}}td,th{{padding:10px;border-bottom:1px solid #163;text-align:left}}.total{{font-size:34px;color:#20ff29;font-weight:900}}.footer{{margin-top:22px;padding-top:14px;border-top:1px solid #184523;color:#93a39b;font-size:13px;text-align:center}}</style></head><body><div class="card"><h1>{s.get('business_name','Bodega Chebitas')}</h1><h2>{cst.name}</h2><div class="note">Este enlace es público y solo de lectura. Aquí el cliente solo puede consultar su deuda y descargar el PDF.</div><table><tr><th>Producto</th><th>Cant.</th><th>P.Unit</th><th>Total</th></tr>{rows}</table><p class="total">S/ {cst.total_current:.2f}</p><p><a style="color:#20ff29" href="/public/credit/{cst.public_token}/pdf">Descargar PDF</a></p><div class="footer">{footer}</div></div></body></html>"""