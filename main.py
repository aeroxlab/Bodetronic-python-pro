import base64
import hashlib
import hmac
import io
import json
import os
import shutil
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import requests
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, ImageFilter
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

# =====================
# CONFIG
# =====================
APP_NAME = os.getenv("APP_NAME", "Bodetronic")
SECRET_KEY = os.getenv("SECRET_KEY", "bodetronic-seguro-2026")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bodetronic.db")
MASTER_USER = os.getenv("MASTER_USER", "73221820")
MASTER_PASS = os.getenv("MASTER_PASS", "jdiazg20")
SUPPORT_WHATSAPP = os.getenv("SUPPORT_WHATSAPP", "51992657332")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# =====================
# MODELS
# =====================
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), default="Jorge Diaz")
    username = Column(String(80), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50), default="MASTER")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    business_name = Column(String(160), index=True)
    owner_name = Column(String(160), default="")
    dni_ruc = Column(String(40), index=True)
    whatsapp = Column(String(40), default="")
    email = Column(String(160), default="")
    address = Column(String(250), default="")
    business_type = Column(String(80), default="Bodega")
    status = Column(String(40), default="ACTIVO")
    membership_type = Column(String(80), default="Demo")
    access_starts_at = Column(DateTime, nullable=True)
    access_expires_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    access = relationship("Access", back_populates="client", uselist=False)
    design = relationship("ClientDesign", back_populates="client", uselist=False)
    services = relationship("ServiceActivation", back_populates="client")
    payments = relationship("PaymentMethod", back_populates="client")
    products = relationship("Product", back_populates="client")

class Access(Base):
    __tablename__ = "accesses"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    username = Column(String(90), unique=True, index=True)
    password_hash = Column(String(255))
    raw_hint = Column(String(120), default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="access")

class ServiceActivation(Base):
    __tablename__ = "service_activations"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    service_key = Column(String(80), index=True)
    service_name = Column(String(140), default="")
    active = Column(Boolean, default=True)
    demo = Column(Boolean, default=False)
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="services")

class ClientDesign(Base):
    __tablename__ = "client_designs"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True)
    title = Column(String(180), default="")
    logo_url = Column(Text, default="")
    primary_color = Column(String(30), default="#00A6A6")
    secondary_color = Column(String(30), default="#0F172A")
    background_color = Column(String(30), default="#ECFEFF")
    background_url = Column(Text, default="")
    button_radius = Column(Integer, default=18)
    font_size = Column(Integer, default=16)
    banner_text = Column(Text, default="")
    sponsor_text = Column(Text, default="")
    visible_buttons = Column(Text, default="")
    visible_info = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="design")

class SystemDesign(Base):
    __tablename__ = "system_design"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text, default="")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    label = Column(String(140), default="Pago principal")
    method = Column(String(80), default="Yape")
    holder_name = Column(String(160), default="")
    phone = Column(String(50), default="")
    qr_url = Column(Text, default="")
    message = Column(Text, default="")
    active = Column(Boolean, default=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="payments")

class Advertisement(Base):
    __tablename__ = "advertisements"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    title = Column(String(180), default="")
    text_body = Column(Text, default="")
    media_url = Column(Text, default="")
    media_type = Column(String(60), default="image")
    location = Column(String(100), default="home")
    display_mode = Column(String(80), default="card")
    sponsor_name = Column(String(180), default="")
    link_url = Column(Text, default="")
    width = Column(String(40), default="100%")
    height = Column(String(40), default="auto")
    duration_seconds = Column(Integer, default=8)
    entrance_style = Column(String(80), default="fade")
    fit_mode = Column(String(50), default="cover")
    bg_color = Column(String(40), default="#0F172A")
    text_color = Column(String(40), default="#FFFFFF")
    font_size = Column(Integer, default=16)
    speed = Column(Integer, default=16)
    active = Column(Boolean, default=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    service = Column(String(80), default="bodega")
    internal_code = Column(String(80), index=True)
    barcode = Column(String(140), default="", index=True)
    reference = Column(String(160), default="", index=True)
    name = Column(String(200), index=True)
    brand = Column(String(160), default="")
    category = Column(String(120), default="")
    presentation = Column(String(120), default="")
    image_url = Column(Text, default="")
    visual_hash = Column(String(120), default="")
    stock = Column(Float, default=0)
    min_stock = Column(Float, default=1)
    real_price = Column(Float, default=0)
    margin = Column(Float, default=30)
    sale_price = Column(Float, default=0)
    expiration_date = Column(String(40), default="")
    active = Column(Boolean, default=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    image_url = Column(Text, default="")
    visual_hash = Column(String(120), default="")
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    product = relationship("Product", back_populates="images")

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    movement_type = Column(String(40), default="")
    quantity = Column(Float, default=0)
    old_stock = Column(Float, default=0)
    new_stock = Column(Float, default=0)
    origin = Column(String(80), default="Manual")
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    service = Column(String(80), default="bodega_pos")
    customer_name = Column(String(180), default="Cliente general")
    customer_phone = Column(String(50), default="")
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_method = Column(String(80), default="Efectivo")
    status = Column(String(40), default="PAGADO")
    ticket_token = Column(String(120), unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), default="")
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    total = Column(Float, default=0)

class CreditCustomer(Base):
    __tablename__ = "credit_customers"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String(180), index=True)
    whatsapp = Column(String(50), default="")
    active = Column(Boolean, default=True)
    total_current = Column(Float, default=0)
    public_token = Column(String(120), unique=True, index=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

class CreditItem(Base):
    __tablename__ = "credit_items"
    id = Column(Integer, primary_key=True)
    credit_customer_id = Column(Integer, ForeignKey("credit_customers.id"), index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200), default="")
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    total = Column(Float, default=0)
    picked_by = Column(String(180), default="")
    notes = Column(Text, default="")
    status = Column(String(40), default="PENDIENTE")
    created_at = Column(DateTime, server_default=func.now())

class CreditPayment(Base):
    __tablename__ = "credit_payments"
    id = Column(Integer, primary_key=True)
    credit_customer_id = Column(Integer, ForeignKey("credit_customers.id"), index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    total_paid = Column(Float, default=0)
    detail_json = Column(Text, default="")
    public_token = Column(String(120), unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

class AutomationSetting(Base):
    __tablename__ = "automation_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(120), unique=True, index=True)
    value = Column(Text, default="")

class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=True)
    channel = Column(String(60), default="")
    destination = Column(String(200), default="")
    message = Column(Text, default="")
    result = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

# =====================
# HELPERS
# =====================
def now():
    return datetime.utcnow()

def peru_time_text(dt: Optional[datetime] = None):
    dt = dt or now()
    peru = dt - timedelta(hours=5)
    return peru.strftime("%d/%m/%Y %H:%M")

def money(v):
    return f"S/ {float(v or 0):.2f}"

def public_url(path: str):
    if BASE_URL:
        return BASE_URL + path
    return path

def hash_password(password: str, salt: Optional[str] = None):
    salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode(), salt.encode(), 120000)
    return f"{salt}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, stored: str):
    try:
        salt, _ = stored.split("$", 1)
        return hmac.compare_digest(hash_password(password, salt), stored)
    except Exception:
        return False

def create_token(payload: dict, expires_hours: int = 72):
    data = dict(payload)
    data["exp"] = int(time.time()) + expires_hours * 3600
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"

def read_token(token: str):
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        data = json.loads(raw)
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def auth_user(authorization: str = Header(default="")):
    token = authorization.replace("Bearer", "").strip()
    data = read_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token inválido")
    return data

def require_admin(user=Depends(auth_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    return user

def require_user(user=Depends(auth_user)):
    if user.get("role") not in ["admin", "client"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    return user

def clean_slug(text: str):
    text = (text or "cliente").lower()
    text = "".join(ch for ch in text if ch.isalnum())
    return text[:22] or "cliente"

def save_upload(file: UploadFile, folder: str = "general"):
    folder_path = UPLOAD_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file.bin").suffix.lower()
    name = f"{uuid.uuid4().hex}{ext}"
    dest = folder_path / name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/{folder}/{name}"

def _hex_hamming(a: str, b: str):
    if not a or not b:
        return None
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except Exception:
        return None

def _bits_to_hex(bits: str):
    return f"{int(bits or '0', 2):0{max(1, (len(bits)+3)//4)}x}"

def _open_visual_image(path: str):
    img = Image.open(path).convert("RGB")
    img.thumbnail((640, 640))
    return img

def _avg_hash_from_image(img, size=8):
    g = ImageOps.autocontrast(img.convert("L")).resize((size, size))
    px = list(g.getdata())
    avg = sum(px) / max(1, len(px))
    return _bits_to_hex("".join("1" if p > avg else "0" for p in px)).zfill(16)

def _diff_hash_from_image(img, size=8):
    g = ImageOps.autocontrast(img.convert("L")).resize((size + 1, size))
    px = list(g.getdata())
    bits = []
    for y in range(size):
        row = px[y * (size + 1):(y + 1) * (size + 1)]
        for x in range(size):
            bits.append("1" if row[x] > row[x + 1] else "0")
    return _bits_to_hex("".join(bits)).zfill(16)

def _edge_hash_from_image(img, size=8):
    g = ImageOps.autocontrast(img.convert("L")).filter(ImageFilter.FIND_EDGES).resize((size, size))
    px = list(g.getdata())
    avg = sum(px) / max(1, len(px))
    return _bits_to_hex("".join("1" if p > avg else "0" for p in px)).zfill(16)

def _color_signature_from_image(img):
    small = img.resize((64, 64)).convert("RGB")
    pixels = list(small.getdata())
    # 24 valores: 8 rangos por canal. Se guarda compacto en hexadecimal.
    counts = [[0] * 8 for _ in range(3)]
    for r, g, b in pixels:
        counts[0][min(7, r // 32)] += 1
        counts[1][min(7, g // 32)] += 1
        counts[2][min(7, b // 32)] += 1
    sig = []
    total = max(1, len(pixels))
    for channel in counts:
        for c in channel:
            sig.append(format(min(15, round((c / total) * 64)), "x"))
    return "".join(sig)

def _crop_hash_pack(img, box_name: str):
    """Hash por zonas para comparar etiqueta, marca, forma y partes del producto."""
    w, h = img.size
    boxes = {
        "center": (int(w*0.18), int(h*0.18), int(w*0.82), int(h*0.82)),
        "label": (int(w*0.12), int(h*0.35), int(w*0.88), int(h*0.78)),
        "top": (0, 0, w, int(h*0.45)),
        "bottom": (0, int(h*0.45), w, h),
        "left": (0, 0, int(w*0.55), h),
        "right": (int(w*0.45), 0, w, h),
    }
    box = boxes.get(box_name, boxes["center"])
    crop = img.crop(box)
    return _avg_hash_from_image(crop) + _diff_hash_from_image(crop) + _edge_hash_from_image(crop)

def _text_like_signature_from_image(img):
    """Firma de letras/textos sin OCR externo.
    Detecta patrones de alto contraste, bordes y distribución de trazos.
    Sirve para comparar marcas, etiquetas, tipografías y códigos visibles,
    aunque no lee palabras como un OCR real.
    """
    g = ImageOps.autocontrast(img.convert("L"))
    w, h = g.size
    # Zona donde normalmente está la etiqueta del producto
    crop = g.crop((int(w*0.08), int(h*0.25), int(w*0.92), int(h*0.86))).resize((96, 64))
    edge = crop.filter(ImageFilter.FIND_EDGES)
    px = list(edge.getdata())
    avg = sum(px) / max(1, len(px))
    binary = [1 if p > max(28, avg * 1.20) else 0 for p in px]

    # Proyección horizontal y vertical: muy útil para letras, líneas y códigos.
    rows = []
    for y in range(64):
        rows.append(sum(binary[y*96:(y+1)*96]))
    cols = []
    for x in range(96):
        cols.append(sum(binary[y*96+x] for y in range(64)))

    def pack(vals, groups):
        step = max(1, len(vals)//groups)
        out = []
        maxv = max(vals) or 1
        for i in range(groups):
            chunk = vals[i*step:(i+1)*step] or [0]
            v = round((sum(chunk)/len(chunk))/maxv*15)
            out.append(format(min(15, max(0, v)), "x"))
        return "".join(out)

    # 16 + 16 + edgehash = letras/códigos/contornos/tipografía
    return pack(rows, 16) + pack(cols, 16) + _edge_hash_from_image(crop)

def _dominant_color_signature_from_image(img):
    """Firma compacta de colores dominantes por cuantización."""
    small = img.resize((48, 48)).convert("RGB")
    buckets = {}
    for r, g, b in small.getdata():
        key = (r//48, g//48, b//48)
        buckets[key] = buckets.get(key, 0) + 1
    top = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:8]
    return "".join(f"{k[0]:x}{k[1]:x}{k[2]:x}{min(15, round(v/2304*80)):x}" for k, v in top).ljust(32, "0")

def _label_hue_signature_from_image(img):
    """Firma de color enfocada en la etiqueta/zona central del producto.
    Cuenta colores saturados por tono. Sirve para diferenciar, por ejemplo,
    etiqueta azul de agua vs etiqueta amarilla/verde de gaseosa.
    """
    w, h = img.size
    crop = img.crop((int(w*0.18), int(h*0.28), int(w*0.86), int(h*0.82))).resize((96, 96)).convert("HSV")
    hue_bins = [0] * 12
    sat_bins = [0] * 6
    val_bins = [0] * 6
    colored = 0
    for hh, ss, vv in crop.getdata():
        if ss >= 45 and vv >= 35:
            hue_bins[min(11, int(hh / 256 * 12))] += 1
            sat_bins[min(5, ss // 43)] += 1
            val_bins[min(5, vv // 43)] += 1
            colored += 1
    total = max(1, colored)
    def pack(vals, scale=64):
        return "".join(format(min(15, round((v / total) * scale)), "x") for v in vals)
    color_amount = format(min(15, round((colored / (96*96)) * 40)), "x")
    return pack(hue_bins) + pack(sat_bins) + pack(val_bins) + color_amount

def image_avg_hash(path: str):
    """Firma visual compatible mejorada.
    v4 compara: forma general, bordes, colores, etiqueta, patrones de letras,
    logos/códigos visuales y color vivo de etiqueta. Es más estricta para evitar
    falsos positivos entre productos de forma parecida.
    """
    try:
        img = _open_visual_image(path)
        return "v4|" + "|".join([
            _avg_hash_from_image(img),
            _diff_hash_from_image(img),
            _edge_hash_from_image(img),
            _color_signature_from_image(img),
            _crop_hash_pack(img, "center"),
            _crop_hash_pack(img, "label"),
            _crop_hash_pack(img, "top"),
            _crop_hash_pack(img, "bottom"),
            _text_like_signature_from_image(img),
            _dominant_color_signature_from_image(img),
            _label_hue_signature_from_image(img)
        ])
    except Exception:
        return ""

def _parse_v2_signature(sig: str):
    if not sig or not sig.startswith("v2|"):
        return None
    parts = sig.split("|")
    if len(parts) != 5:
        return None
    return {"avg": parts[1], "diff": parts[2], "edge": parts[3], "color": parts[4]}

def _parse_v3_signature(sig: str):
    if not sig or not sig.startswith("v3|"):
        return None
    parts = sig.split("|")
    if len(parts) != 11:
        return None
    return {
        "avg": parts[1], "diff": parts[2], "edge": parts[3], "color": parts[4],
        "center": parts[5], "label": parts[6], "top": parts[7], "bottom": parts[8],
        "textlike": parts[9], "dominant": parts[10]
    }

def _parse_v4_signature(sig: str):
    if not sig or not sig.startswith("v4|"):
        return None
    parts = sig.split("|")
    if len(parts) != 12:
        return None
    return {
        "avg": parts[1], "diff": parts[2], "edge": parts[3], "color": parts[4],
        "center": parts[5], "label": parts[6], "top": parts[7], "bottom": parts[8],
        "textlike": parts[9], "dominant": parts[10], "label_hue": parts[11]
    }

def _hex_distance_percent(a: str, b: str):
    if not a or not b:
        return 100
    m = min(len(a), len(b))
    if m <= 0:
        return 100
    aa, bb = a[:m], b[:m]
    d = _hex_hamming(aa, bb)
    if d is None:
        return 100
    return (d / max(1, m * 4)) * 100

def _signature_color_distance(a: str, b: str):
    try:
        m = min(len(a), len(b))
        ca = [int(x, 16) for x in a[:m]]
        cb = [int(x, 16) for x in b[:m]]
        return sum(abs(x - y) for x, y in zip(ca, cb)) / max(1, 15 * len(ca)) * 100
    except Exception:
        return 100

def _label_hue_hist_distance(a: str, b: str):
    """Distancia por intersección de tonos de etiqueta.
    0 = tonos muy parecidos, 100 = tonos muy diferentes.
    Usa solo los 12 primeros bins de tono guardados por _label_hue_signature_from_image.
    Esto diferencia mejor etiqueta azul vs amarilla/verde sin depender tanto del fondo o mano.
    """
    try:
        ha = [int(x, 16) for x in (a or '')[:12]]
        hb = [int(x, 16) for x in (b or '')[:12]]
        if len(ha) < 12 or len(hb) < 12:
            return 100
        sa, sb = sum(ha), sum(hb)
        if sa <= 0 or sb <= 0:
            return 100
        na = [x / sa for x in ha]
        nb = [x / sb for x in hb]
        overlap = sum(min(x, y) for x, y in zip(na, nb))
        return round((1 - overlap) * 100, 2)
    except Exception:
        return 100

def visual_distance(a: str, b: str):
    """Menor puntaje = más parecido.
    v3 revisa detalles mínimos: forma, bordes, etiqueta, letras/códigos visuales,
    color, tipografía aproximada y zonas del producto.
    """
    if not a or not b:
        return None

    av4, bv4 = _parse_v4_signature(a), _parse_v4_signature(b)
    if av4 and bv4:
        d_avg = _hex_distance_percent(av4["avg"], bv4["avg"])
        d_diff = _hex_distance_percent(av4["diff"], bv4["diff"])
        d_edge = _hex_distance_percent(av4["edge"], bv4["edge"])
        d_color = _signature_color_distance(av4["color"], bv4["color"])
        d_center = _hex_distance_percent(av4["center"], bv4["center"])
        d_label = _hex_distance_percent(av4["label"], bv4["label"])
        d_text = _hex_distance_percent(av4["textlike"], bv4["textlike"])
        d_dom = _signature_color_distance(av4["dominant"], bv4["dominant"])
        d_label_hue = _label_hue_hist_distance(av4["label_hue"], bv4["label_hue"])

        score = (
            d_avg * 0.03 +
            d_diff * 0.08 +
            d_edge * 0.06 +
            d_color * 0.05 +
            d_center * 0.10 +
            d_label * 0.17 +
            d_text * 0.13 +
            d_dom * 0.05 +
            d_label_hue * 0.33
        )
        return round(score, 2)

    av3, bv3 = _parse_v3_signature(a), _parse_v3_signature(b)
    if av3 and bv3:
        d_avg = _hex_distance_percent(av3["avg"], bv3["avg"])
        d_diff = _hex_distance_percent(av3["diff"], bv3["diff"])
        d_edge = _hex_distance_percent(av3["edge"], bv3["edge"])
        d_color = _signature_color_distance(av3["color"], bv3["color"])
        d_center = _hex_distance_percent(av3["center"], bv3["center"])
        d_label = _hex_distance_percent(av3["label"], bv3["label"])
        d_top = _hex_distance_percent(av3["top"], bv3["top"])
        d_bottom = _hex_distance_percent(av3["bottom"], bv3["bottom"])
        d_text = _hex_distance_percent(av3["textlike"], bv3["textlike"])
        d_dom = _signature_color_distance(av3["dominant"], bv3["dominant"])

        # Pesos afinados para productos: etiqueta/texto + forma + color.
        score = (
            d_avg * 0.08 +
            d_diff * 0.14 +
            d_edge * 0.11 +
            d_color * 0.08 +
            d_center * 0.12 +
            d_label * 0.19 +
            d_top * 0.05 +
            d_bottom * 0.05 +
            d_text * 0.13 +
            d_dom * 0.05
        )
        return round(score, 2)

    # Compatibilidad con v2.
    av2, bv2 = _parse_v2_signature(a), _parse_v2_signature(b)
    if av2 and bv2:
        d_avg = _hex_distance_percent(av2["avg"], bv2["avg"])
        d_diff = _hex_distance_percent(av2["diff"], bv2["diff"])
        d_edge = _hex_distance_percent(av2["edge"], bv2["edge"])
        d_color = _signature_color_distance(av2["color"], bv2["color"])
        return round((d_avg * 0.30) + (d_diff * 0.35) + (d_edge * 0.25) + (d_color * 0.10), 2)

    # Compatibilidad con firmas viejas de 16 hex.
    old = _hex_hamming(a, b)
    return None if old is None else round((old / 64) * 100, 2)

def hash_distance(a: str, b: str):
    # Se conserva el nombre usado antes, pero ahora llama al comparador mejorado.
    return visual_distance(a, b)

def visual_match_details(a: str, b: str):
    """Devuelve score y reglas de coincidencia segura.
    Evita falsos positivos: si solo coincide la forma del envase, NO acepta.
    Debe concordar color vivo de etiqueta, marca/texto visual, zona central, bordes y forma.
    """
    score = visual_distance(a, b)
    details = {"score": score, "safe_match": False}
    if score is None:
        return details

    av4, bv4 = _parse_v4_signature(a), _parse_v4_signature(b)
    if av4 and bv4:
        d_diff = _hex_distance_percent(av4["diff"], bv4["diff"])
        d_edge = _hex_distance_percent(av4["edge"], bv4["edge"])
        d_color = _signature_color_distance(av4["color"], bv4["color"])
        d_center = _hex_distance_percent(av4["center"], bv4["center"])
        d_label = _hex_distance_percent(av4["label"], bv4["label"])
        d_text = _hex_distance_percent(av4["textlike"], bv4["textlike"])
        d_dom = _signature_color_distance(av4["dominant"], bv4["dominant"])
        d_label_hue = _label_hue_hist_distance(av4["label_hue"], bv4["label_hue"])

        strict_score = float(os.getenv("VISUAL_STRICT_SCORE", "38"))
        max_label_hue = float(os.getenv("VISUAL_MAX_LABEL_HUE", "58"))
        max_label_text = float(os.getenv("VISUAL_MAX_LABEL_TEXT", "58"))
        max_center = float(os.getenv("VISUAL_MAX_CENTER", "56"))
        max_shape = float(os.getenv("VISUAL_MAX_SHAPE", "65"))

        good_label_color = d_label_hue <= max_label_hue
        # En fotos de celular puede cambiar el ángulo/luz; por eso se acepta etiqueta o texto,
        # pero nunca se salta el color vivo de la etiqueta.
        good_label_text = min(d_label, d_text) <= max_label_text
        good_center = d_center <= max_center
        good_shape = min(d_diff, d_edge) <= max_shape

        safe = bool(score <= strict_score and good_label_color and (good_label_text or good_center) and good_shape)

        details.update({
            "diff": round(d_diff, 2), "edge": round(d_edge, 2),
            "color": round(d_color, 2), "dominant_color": round(d_dom, 2),
            "label_hue": round(d_label_hue, 2), "center": round(d_center, 2),
            "label": round(d_label, 2), "text_like": round(d_text, 2),
            "good_label_color": good_label_color,
            "good_label_text": good_label_text,
            "good_center": good_center,
            "good_shape": good_shape,
            "safe_match": safe,
            "strict_score": strict_score
        })
        return details

    av3, bv3 = _parse_v3_signature(a), _parse_v3_signature(b)
    if av3 and bv3:
        d_color = _signature_color_distance(av3["color"], bv3["color"])
        d_dom = _signature_color_distance(av3["dominant"], bv3["dominant"])
        d_label = _hex_distance_percent(av3["label"], bv3["label"])
        d_text = _hex_distance_percent(av3["textlike"], bv3["textlike"])
        d_center = _hex_distance_percent(av3["center"], bv3["center"])
        d_diff = _hex_distance_percent(av3["diff"], bv3["diff"])
        d_edge = _hex_distance_percent(av3["edge"], bv3["edge"])
        safe = bool(score <= 24 and min(d_color, d_dom) <= 28 and min(d_label, d_text) <= 28 and min(d_center, d_diff, d_edge) <= 34)
        details.update({
            "color": round(d_color, 2), "dominant_color": round(d_dom, 2),
            "label": round(d_label, 2), "text_like": round(d_text, 2),
            "center": round(d_center, 2), "safe_match": safe
        })
        return details

    details["safe_match"] = bool(score <= float(os.getenv("VISUAL_OLD_STRICT_SCORE", "18")))
    return details

def upload_disk_path(upload_url: str):
    if not upload_url:
        return None
    rel = str(upload_url).replace("/uploads/", "")
    path = UPLOAD_DIR / rel
    return path if path.exists() else None

def ensure_visual_signature(obj, upload_url: str):
    """Recalcula firmas antiguas al detectar, sin pedir al usuario volver a registrar."""
    current = getattr(obj, "visual_hash", "") or ""
    if current.startswith("v4|"):
        return current
    path = upload_disk_path(upload_url)
    if not path:
        return current
    sig = image_avg_hash(str(path))
    if sig:
        obj.visual_hash = sig
        return sig
    return current

def sync_product_images(db, p: Product):
    """Limpieza automática interna de fotos.
    - La comparación usa solo fotos visibles en ProductImage.
    - Si product.image_url quedó apuntando a una foto antigua/oculta, se reemplaza por la primera foto visible.
    - Borra referencias duplicadas o sin archivo real.
    - Recalcula firmas visuales antiguas a V4.
    """
    if not p:
        return []

    raw = db.query(ProductImage).filter(ProductImage.product_id == p.id).order_by(ProductImage.position.asc(), ProductImage.id.asc()).all()
    visible = []
    seen = set()

    for img in raw:
        url = (img.image_url or "").strip()
        # Sin URL o duplicada: se elimina para que no participe en comparación.
        if not url or url in seen:
            db.delete(img)
            continue
        # Si el archivo ya no existe en uploads, se elimina la referencia.
        if not upload_disk_path(url):
            db.delete(img)
            continue
        seen.add(url)
        ensure_visual_signature(img, url)
        visible.append(img)

    db.flush()

    # Si existe imagen principal antigua pero NO está visible, no se compara.
    # Se sincroniza automáticamente con una foto visible.
    visible_urls = [i.image_url for i in visible]
    if visible:
        if p.image_url not in visible_urls:
            p.image_url = visible[0].image_url
            p.visual_hash = ensure_visual_signature(visible[0], visible[0].image_url)
        else:
            # Asegurar hash principal V4.
            principal = next((i for i in visible if i.image_url == p.image_url), visible[0])
            p.visual_hash = ensure_visual_signature(principal, principal.image_url)

        # Orden interno: principal primero, referencias después.
        for img in visible:
            img.position = 0 if img.image_url == p.image_url else 1
    else:
        # Compatibilidad: si no hay fotos visibles, pero image_url existe y archivo existe,
        # se crea una referencia visible única. Si no existe el archivo, se limpia.
        if p.image_url and upload_disk_path(p.image_url):
            sig = ensure_visual_signature(p, p.image_url)
            img = ProductImage(product_id=p.id, client_id=p.client_id, image_url=p.image_url, visual_hash=sig, position=0)
            db.add(img)
            db.flush()
            visible = [img]
        else:
            p.image_url = ""
            p.visual_hash = ""

    return visible

def sync_client_products_images(db, client_id: int):
    products = db.query(Product).filter(Product.client_id == client_id).all()
    for p in products:
        sync_product_images(db, p)
    db.commit()

SERVICE_NAMES = {
    "bodega": "Bodega",
    "bodega_pos": "Bodega - Punto de venta",
    "bodega_credits": "Bodega - Créditos/Cuentas",
    "bodega_expirations": "Bodega - Vencimientos",
    "minimarket": "Minimarket",
    "minimarket_pos": "Minimarket - Punto de venta",
    "minimarket_credits": "Minimarket - Créditos/Cuentas",
    "minimarket_expirations": "Minimarket - Vencimientos",
    "almacen": "Almacén",
    "almacen_picking": "Almacén - Picking",
    "almacen_pos": "Almacén - Punto de venta",
}

def calc_expiration(duration_type: str = "indefinido", amount: int = 0):
    duration_type = (duration_type or "indefinido").lower()
    amount = int(amount or 0)
    if duration_type in ["indefinido", "sin_limite", "ilimitado"] or amount <= 0:
        return None
    if duration_type in ["hora", "horas"]:
        return now() + timedelta(hours=amount)
    if duration_type in ["dia", "dias", "día", "días"]:
        return now() + timedelta(days=amount)
    if duration_type in ["mes", "meses"]:
        return now() + timedelta(days=30 * amount)
    return None

def is_active_service(row: ServiceActivation):
    if not row or not row.active:
        return False
    if row.expires_at and row.expires_at < now():
        return False
    return True

def service_map(client: Client):
    data = {}
    for k in SERVICE_NAMES:
        data[k] = {"active": False, "expires_at": None, "demo": False, "name": SERVICE_NAMES[k]}
    for s in client.services:
        data[s.service_key] = {
            "active": is_active_service(s),
            "expires_at": s.expires_at.isoformat() if s.expires_at else "INDEFINIDO",
            "demo": bool(s.demo),
            "name": s.service_name or SERVICE_NAMES.get(s.service_key, s.service_key),
        }
    return data

def client_is_active(c: Client):
    if not c or c.status.upper() != "ACTIVO":
        return False
    if c.access_expires_at and c.access_expires_at < now():
        return False
    return True

def client_dict(c: Client):
    return {
        "id": c.id,
        "business_name": c.business_name,
        "owner_name": c.owner_name,
        "dni_ruc": c.dni_ruc,
        "whatsapp": c.whatsapp,
        "email": c.email,
        "address": c.address,
        "business_type": c.business_type,
        "status": "VENCIDO" if c.access_expires_at and c.access_expires_at < now() else c.status,
        "membership_type": c.membership_type,
        "access_starts_at": c.access_starts_at.isoformat() if c.access_starts_at else "",
        "access_expires_at": c.access_expires_at.isoformat() if c.access_expires_at else "INDEFINIDO",
        "notes": c.notes,
        "created_at": str(c.created_at) if c.created_at else "",
    }

def design_dict(d: Optional[ClientDesign], c: Optional[Client] = None):
    return {
        "title": (d.title if d and d.title else (c.business_name if c else "")),
        "logo_url": d.logo_url if d else "",
        "primary_color": d.primary_color if d else "#00A6A6",
        "secondary_color": d.secondary_color if d else "#0F172A",
        "background_color": d.background_color if d else "#ECFEFF",
        "background_url": d.background_url if d else "",
        "button_radius": d.button_radius if d else 18,
        "font_size": d.font_size if d else 16,
        "banner_text": d.banner_text if d else "",
        "sponsor_text": d.sponsor_text if d else "",
        "visible_buttons": d.visible_buttons if d else "",
        "visible_info": d.visible_info if d else "",
    }


def product_display_name(p: Product):
    """Nombre visible: nombre + marca sin duplicar.
    Si el nombre tiene presentación/cantidad, inserta la marca antes del primer número:
    agua 1litro + San Luis -> agua San Luis 1litro.
    """
    name = (p.name or "").strip()
    brand = (p.brand or "").strip()
    if not brand:
        return name
    if brand.lower() in name.lower():
        return name
    m = re.search(r"\b\d", name)
    if m:
        before = name[:m.start()].strip()
        after = name[m.start():].strip()
        return " ".join([x for x in [before, brand, after] if x]).strip()
    return f"{name} {brand}".strip()

def product_dict(p: Product):
    imgs = sorted([img for img in getattr(p, "images", []) if img.image_url], key=lambda x: (0 if x.image_url == p.image_url else 1, x.position or 0, x.id or 0))
    visible_urls = [img.image_url for img in imgs]
    main_url = p.image_url if p.image_url in visible_urls else (visible_urls[0] if visible_urls else "")
    return {
        "id": p.id,
        "client_id": p.client_id,
        "service": p.service,
        "internal_code": p.internal_code,
        "barcode": p.barcode,
        "reference": p.reference,
        "name": p.name,
        "display_name": product_display_name(p),
        "brand": p.brand,
        "category": p.category,
        "presentation": p.presentation,
        "image_url": main_url,
        "images": visible_urls,
        "image_items": [{"id": img.id, "url": img.image_url, "position": img.position} for img in imgs],
        "image_count": len(imgs),
        "stock": p.stock,
        "min_stock": p.min_stock,
        "real_price": p.real_price,
        "sale_price": p.sale_price,
        "expiration_date": p.expiration_date,
        "active": p.active,
        "notes": p.notes,
    }

def payment_dict(p: PaymentMethod):
    return {
        "id": p.id, "client_id": p.client_id, "label": p.label, "method": p.method,
        "holder_name": p.holder_name, "phone": p.phone, "qr_url": p.qr_url,
        "message": p.message, "active": p.active, "position": p.position
    }

def setting(db, key, default=""):
    row = db.query(AutomationSetting).filter(AutomationSetting.key == key).first()
    return row.value if row else default

def set_setting(db, key, value):
    row = db.query(AutomationSetting).filter(AutomationSetting.key == key).first()
    if not row:
        db.add(AutomationSetting(key=key, value=str(value or "")))
    else:
        row.value = str(value or "")
    db.commit()

def call_webhook(url, payload):
    if not url:
        return {"ok": False, "error": "Webhook no configurado"}
    try:
        r = requests.post(url, json=payload, timeout=25)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "text": r.text[:1000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def ensure_sqlite_schema():
    # Render/SQLite no agrega columnas nuevas con create_all. Esta mini migración
    # mantiene el sistema compatible cuando actualizamos el paquete.
    if not DATABASE_URL.startswith("sqlite"):
        return
    try:
        with engine.connect() as conn:
            sales_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(sales)").fetchall()]
            if "customer_phone" not in sales_cols:
                conn.exec_driver_sql("ALTER TABLE sales ADD COLUMN customer_phone VARCHAR(50) DEFAULT ''")

            ad_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(advertisements)").fetchall()]
            ad_add = {
                "text_body": "TEXT DEFAULT ''",
                "display_mode": "VARCHAR(80) DEFAULT 'card'",
                "width": "VARCHAR(40) DEFAULT '100%'",
                "height": "VARCHAR(40) DEFAULT 'auto'",
                "duration_seconds": "INTEGER DEFAULT 8",
                "entrance_style": "VARCHAR(80) DEFAULT 'fade'",
                "fit_mode": "VARCHAR(50) DEFAULT 'cover'",
                "bg_color": "VARCHAR(40) DEFAULT '#0F172A'",
                "text_color": "VARCHAR(40) DEFAULT '#FFFFFF'",
                "font_size": "INTEGER DEFAULT 16",
                "speed": "INTEGER DEFAULT 16",
            }
            for col, sql in ad_add.items():
                if col not in ad_cols:
                    conn.exec_driver_sql(f"ALTER TABLE advertisements ADD COLUMN {col} {sql}")
            conn.commit()
    except Exception:
        pass

def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == MASTER_USER).first()
        if not admin:
            db.add(Admin(name="Jorge Diaz", username=MASTER_USER, password_hash=hash_password(MASTER_PASS), role="MASTER", active=True))
        defaults = {
            "whatsapp_webhook": "",
            "email_webhook": "",
            "event_webhook": "",
            "visual_ai_webhook": "",
            "reminder_template": "Hola {{cliente}}, te escribimos de {{negocio}}. {{mensaje}}",
        }
        for k, v in defaults.items():
            if not db.query(AutomationSetting).filter(AutomationSetting.key == k).first():
                db.add(AutomationSetting(key=k, value=v))
        for k, v in {
            "system_app_name": "Bodetronic",
            "system_subtitle": "Inventario, registro y precios",
            "system_primary_color": "#00A6A6",
            "system_secondary_color": "#0F172A",
            "system_background": "#ECFEFF",
            "system_background_url": "",
            "system_logo": "",
            "system_button_radius": "18",
            "system_card_radius": "22",
            "system_font_size": "16",
            "system_footer_brand": "AeroxLab",
            "system_footer_team": "WEB DEVELOPER TEAM",
            "system_footer_rights": "© 2025-2026 Aerox Security Consulting LLC",
            "system_privacy_text": "Derechos reservados | Políticas de privacidad",
        }.items():
            if not db.query(SystemDesign).filter(SystemDesign.key == k).first():
                db.add(SystemDesign(key=k, value=v))
        db.commit()
    finally:
        db.close()

# =====================
# APP
# =====================
app = FastAPI(title="Bodetronic Python Pro Final")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("static/index.html")

# =====================
# AUTH
# =====================
@app.post("/api/auth/login")
def login(payload: dict, db=Depends(get_db)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()

    admin = db.query(Admin).filter(Admin.username == username, Admin.active == True).first()
    if admin and verify_password(password, admin.password_hash):
        return {"ok": True, "role": "admin", "token": create_token({"role": "admin", "admin_id": admin.id, "username": admin.username})}

    access = db.query(Access).filter(Access.username == username, Access.active == True).first()
    if access and verify_password(password, access.password_hash):
        c = db.query(Client).get(access.client_id)
        if not client_is_active(c):
            return {"ok": False, "error": "Acceso vencido o inactivo"}
        access.last_login = now()
        db.commit()
        return {"ok": True, "role": "client", "token": create_token({"role": "client", "client_id": c.id, "username": access.username}), "client": client_dict(c)}

    return {"ok": False, "error": "Credenciales incorrectas"}

# =====================
# UPLOAD
# =====================
@app.post("/api/upload")
def upload_file(folder: str = Form("general"), file: UploadFile = File(...), user=Depends(require_user)):
    return {"ok": True, "url": save_upload(file, folder)}

# =====================
# ADMIN
# =====================
@app.get("/api/admin/dashboard")
def admin_dashboard(db=Depends(get_db), user=Depends(require_admin)):
    clients = db.query(Client).all()
    visible = [c for c in clients if c.status.upper() not in ["OCULTO", "ARCHIVADO", "ELIMINADO"]]
    return {"ok": True, "stats": {
        "clients": len(visible),
        "active": len([c for c in visible if client_is_active(c)]),
        "expired": len([c for c in visible if c.access_expires_at and c.access_expires_at < now()]),
        "products": db.query(Product).filter(Product.active == True).count(),
        "sales": db.query(Sale).count(),
        "credits_total": sum([x.total_current for x in db.query(CreditCustomer).all()]),
    }}

@app.get("/api/admin/clients")
def admin_clients(db=Depends(get_db), user=Depends(require_admin)):
    clients = db.query(Client).order_by(Client.id.desc()).all()
    out = []
    for c in clients:
        d = client_dict(c)
        d["access"] = {"username": c.access.username if c.access else "", "password": c.access.raw_hint if c.access else ""}
        d["services"] = service_map(c)
        d["design"] = design_dict(c.design, c)
        out.append(d)
    return {"ok": True, "clients": out}

@app.post("/api/admin/clients")
def admin_create_client(payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    business = str(payload.get("business_name") or payload.get("negocio") or "").strip()
    dni = str(payload.get("dni_ruc") or payload.get("dni") or "").strip()
    if not business or not dni:
        return {"ok": False, "error": "Completa negocio y DNI/RUC"}

    username = str(payload.get("username") or clean_slug(business)).strip()
    raw_password = str(payload.get("password") or dni).strip()
    duration_type = payload.get("duration_type", "indefinido")
    duration_amount = int(payload.get("duration_amount") or 0)
    expires_at = calc_expiration(duration_type, duration_amount)

    c = Client(
        business_name=business,
        owner_name=payload.get("owner_name", ""),
        dni_ruc=dni,
        whatsapp=payload.get("whatsapp", ""),
        email=payload.get("email", ""),
        address=payload.get("address", ""),
        business_type=payload.get("business_type", "Bodega"),
        status="ACTIVO",
        membership_type=payload.get("membership_type", "Demo"),
        access_starts_at=now(),
        access_expires_at=expires_at,
        notes=payload.get("notes", "")
    )
    db.add(c)
    db.flush()

    db.add(Access(client_id=c.id, username=username, password_hash=hash_password(raw_password), raw_hint=raw_password, active=True))
    db.add(ClientDesign(client_id=c.id, title=business))
    db.add(PaymentMethod(client_id=c.id, label="Pago principal", method="Yape", holder_name=business, active=True, position=1))

    services = payload.get("services", {})
    for k, active in services.items():
        if k in SERVICE_NAMES and active:
            db.add(ServiceActivation(
                client_id=c.id, service_key=k, service_name=SERVICE_NAMES[k],
                active=True, demo=payload.get("membership_type", "Demo").lower().find("demo") >= 0,
                starts_at=now(), expires_at=expires_at
            ))
    db.commit()
    return {"ok": True, "client": client_dict(c), "username": username, "password": raw_password}

@app.put("/api/admin/clients/{client_id}/access")
def admin_update_access(client_id: int, payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    c = db.query(Client).get(client_id)
    if not c:
        return {"ok": False, "error": "Cliente no encontrado"}
    if "status" in payload:
        c.status = payload["status"]
    if "duration_type" in payload:
        c.access_starts_at = now()
        c.access_expires_at = calc_expiration(payload.get("duration_type"), int(payload.get("duration_amount") or 0))
    if c.access:
        c.access.active = c.status.upper() == "ACTIVO"
        if payload.get("username"):
            c.access.username = payload["username"]
        if payload.get("password"):
            c.access.raw_hint = payload["password"]
            c.access.password_hash = hash_password(payload["password"])
    db.commit()
    return {"ok": True, "client": client_dict(c)}

@app.put("/api/admin/clients/{client_id}/services")
def admin_update_services(client_id: int, payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    c = db.query(Client).get(client_id)
    if not c:
        return {"ok": False, "error": "Cliente no encontrado"}

    services = payload.get("services", payload)
    duration_type = payload.get("duration_type", "indefinido")
    duration_amount = int(payload.get("duration_amount") or 0)
    expires_at = calc_expiration(duration_type, duration_amount)
    demo = bool(payload.get("demo", False))

    for k, active in services.items():
        if k not in SERVICE_NAMES:
            continue
        row = db.query(ServiceActivation).filter(ServiceActivation.client_id == client_id, ServiceActivation.service_key == k).first()
        if not row:
            row = ServiceActivation(client_id=client_id, service_key=k, service_name=SERVICE_NAMES[k])
            db.add(row)
        row.active = bool(active)
        row.demo = demo
        row.starts_at = now()
        row.expires_at = expires_at
    db.commit()
    return {"ok": True, "services": service_map(c)}

@app.put("/api/admin/clients/{client_id}/design")
def admin_update_design(client_id: int, payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    c = db.query(Client).get(client_id)
    if not c:
        return {"ok": False, "error": "Cliente no encontrado"}
    d = c.design or ClientDesign(client_id=client_id)
    for k in ["title", "logo_url", "primary_color", "secondary_color", "background_color", "background_url", "banner_text", "sponsor_text", "visible_buttons", "visible_info"]:
        if k in payload:
            setattr(d, k, payload[k] or "")
    if "button_radius" in payload:
        d.button_radius = int(payload.get("button_radius") or 18)
    if "font_size" in payload:
        d.font_size = int(payload.get("font_size") or 16)
    d.updated_at = now()
    db.add(d)
    db.commit()
    return {"ok": True, "design": design_dict(d, c)}

@app.get("/api/admin/system-design")
def get_system_design(db=Depends(get_db), user=Depends(require_admin)):
    rows = db.query(SystemDesign).all()
    return {"ok": True, "design": {r.key: r.value for r in rows}}

@app.put("/api/admin/system-design")
def update_system_design(payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    for k, v in payload.items():
        row = db.query(SystemDesign).filter(SystemDesign.key == k).first()
        if not row:
            row = SystemDesign(key=k, value=str(v or ""))
            db.add(row)
        else:
            row.value = str(v or "")
    db.commit()
    return {"ok": True}

@app.get("/api/admin/ads")
def admin_list_ads(db=Depends(get_db), user=Depends(require_admin)):
    rows = db.query(Advertisement).order_by(Advertisement.id.desc()).all()
    return {"ok": True, "ads": [{
        "id": a.id, "client_id": a.client_id, "title": a.title, "text_body": a.text_body,
        "media_url": a.media_url, "media_type": a.media_type, "location": a.location,
        "display_mode": a.display_mode, "sponsor_name": a.sponsor_name, "link_url": a.link_url,
        "width": a.width, "height": a.height, "duration_seconds": a.duration_seconds,
        "entrance_style": a.entrance_style, "fit_mode": getattr(a, "fit_mode", "cover"), "bg_color": getattr(a, "bg_color", "#0F172A"),
        "text_color": getattr(a, "text_color", "#FFFFFF"), "font_size": getattr(a, "font_size", 16),
        "speed": getattr(a, "speed", 16), "active": a.active,
        "starts_at": a.starts_at.isoformat() if a.starts_at else "",
        "ends_at": a.ends_at.isoformat() if a.ends_at else "",
    } for a in rows]}

@app.post("/api/admin/ads")
def admin_add_ad(payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    ad = Advertisement(
        client_id=payload.get("client_id") or None,
        title=payload.get("title", ""),
        text_body=payload.get("text_body", ""),
        media_url=payload.get("media_url", ""),
        media_type=payload.get("media_type", "image"),
        location=payload.get("location", "home"),
        display_mode=payload.get("display_mode", "card"),
        sponsor_name=payload.get("sponsor_name", ""),
        link_url=payload.get("link_url", ""),
        width=str(payload.get("width") or "100%"),
        height=str(payload.get("height") or "auto"),
        duration_seconds=int(payload.get("duration_seconds") or 8),
        entrance_style=payload.get("entrance_style", "fade"),
        fit_mode=payload.get("fit_mode", "cover"),
        bg_color=payload.get("bg_color", "#0F172A"),
        text_color=payload.get("text_color", "#FFFFFF"),
        font_size=int(payload.get("font_size") or 16),
        speed=int(payload.get("speed") or 16),
        active=bool(payload.get("active", True)),
        starts_at=datetime.fromisoformat(payload["starts_at"]) if payload.get("starts_at") else None,
        ends_at=datetime.fromisoformat(payload["ends_at"]) if payload.get("ends_at") else None,
    )
    db.add(ad)
    db.commit()
    return {"ok": True, "ad_id": ad.id}

@app.put("/api/admin/ads/{ad_id}")
def admin_update_ad(ad_id: int, payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    ad = db.query(Advertisement).get(ad_id)
    if not ad:
        return {"ok": False, "error": "Publicidad no encontrada"}
    for k in ["title", "text_body", "media_url", "media_type", "location", "display_mode", "sponsor_name", "link_url", "width", "height", "entrance_style", "fit_mode", "bg_color", "text_color"]:
        if k in payload:
            setattr(ad, k, payload[k] or "")
    for k in ["duration_seconds", "font_size", "speed"]:
        if k in payload:
            setattr(ad, k, int(payload.get(k) or 0))
    if "client_id" in payload:
        ad.client_id = payload.get("client_id") or None
    if "active" in payload:
        ad.active = bool(payload.get("active"))
    db.commit()
    return {"ok": True}

@app.delete("/api/admin/ads/{ad_id}")
def admin_delete_ad(ad_id: int, db=Depends(get_db), user=Depends(require_admin)):
    ad = db.query(Advertisement).get(ad_id)
    if not ad:
        return {"ok": False, "error": "Publicidad no encontrada"}
    db.delete(ad)
    db.commit()
    return {"ok": True}

# =====================
# CLIENT BUNDLE
# =====================
@app.get("/api/client/bundle")
def client_bundle(client_id: Optional[int] = None, db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client":
        client_id = int(user["client_id"])
    if not client_id:
        return {"ok": False, "error": "Falta cliente"}
    c = db.query(Client).get(client_id)
    if not c:
        return {"ok": False, "error": "Cliente no encontrado"}

    ads = db.query(Advertisement).filter(Advertisement.active == True).all()
    active_ads = []
    for a in ads:
        if a.client_id not in [None, c.id]:
            continue
        if a.starts_at and a.starts_at > now():
            continue
        if a.ends_at and a.ends_at < now():
            continue
        active_ads.append({
            "id": a.id, "title": a.title, "text_body": a.text_body, "media_url": a.media_url,
            "media_type": a.media_type, "location": a.location, "display_mode": a.display_mode,
            "sponsor_name": a.sponsor_name, "link_url": a.link_url, "width": a.width, "height": a.height,
            "duration_seconds": a.duration_seconds, "entrance_style": a.entrance_style,
            "fit_mode": getattr(a, "fit_mode", "cover"),
            "bg_color": getattr(a, "bg_color", "#0F172A"), "text_color": getattr(a, "text_color", "#FFFFFF"),
            "font_size": getattr(a, "font_size", 16), "speed": getattr(a, "speed", 16)
        })

    sync_client_products_images(db, c.id)
    db.refresh(c)

    return {
        "ok": True,
        "client": client_dict(c),
        "services": service_map(c),
        "design": design_dict(c.design, c),
        "payments": [payment_dict(p) for p in sorted(c.payments, key=lambda x: x.position) if p.active],
        "products": [product_dict(p) for p in c.products if p.active],
        "ads": active_ads,
    }

# =====================
# PAYMENTS / QR
# =====================
@app.get("/api/payments")
def list_payments(client_id: int, db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = db.query(PaymentMethod).filter(PaymentMethod.client_id == client_id, PaymentMethod.active == True).order_by(PaymentMethod.position.asc()).all()
    return {"ok": True, "payments": [payment_dict(p) for p in rows]}

@app.post("/api/payments")
def add_payment(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    client_id = int(payload.get("client_id"))
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    p = PaymentMethod(
        client_id=client_id,
        label=payload.get("label", "Pago"),
        method=payload.get("method", "Yape"),
        holder_name=payload.get("holder_name", ""),
        phone=payload.get("phone", ""),
        qr_url=payload.get("qr_url", ""),
        message=payload.get("message", ""),
        active=bool(payload.get("active", True)),
        position=int(payload.get("position") or 0)
    )
    db.add(p)
    db.commit()
    return {"ok": True, "payment": payment_dict(p)}

@app.put("/api/payments/{payment_id}")
def update_payment(payment_id: int, payload: dict, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(PaymentMethod).get(payment_id)
    if not p:
        return {"ok": False, "error": "Pago no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    for k in ["label", "method", "holder_name", "phone", "qr_url", "message"]:
        if k in payload:
            setattr(p, k, payload[k] or "")
    if "active" in payload:
        p.active = bool(payload["active"])
    if "position" in payload:
        p.position = int(payload["position"] or 0)
    db.commit()
    return {"ok": True, "payment": payment_dict(p)}

@app.delete("/api/payments/{payment_id}")
def delete_payment(payment_id: int, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(PaymentMethod).get(payment_id)
    if not p:
        return {"ok": False, "error": "Pago no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    db.delete(p)
    db.commit()
    return {"ok": True}

# =====================
# PRODUCTS / STOCK / VISUAL
# =====================
@app.get("/api/products")
def list_products(client_id: int, db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    sync_client_products_images(db, client_id)
    rows = db.query(Product).filter(Product.client_id == client_id, Product.active == True).order_by(Product.id.desc()).all()
    return {"ok": True, "products": [product_dict(p) for p in rows]}

@app.post("/api/products")
def create_product(
    client_id: int = Form(...),
    name: str = Form(...),
    brand: str = Form(""),
    barcode: str = Form(""),
    reference: str = Form(""),
    category: str = Form(""),
    presentation: str = Form(""),
    stock: float = Form(0),
    min_stock: float = Form(1),
    real_price: float = Form(0),
    sale_price: float = Form(0),
    expiration_date: str = Form(""),
    service: str = Form("bodega"),
    notes: str = Form(""),
    image: UploadFile = File(None),
    images: List[UploadFile] = File(default=[]),
    db=Depends(get_db),
    user=Depends(require_user)
):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    saved_images = []
    upload_list = []
    if image and getattr(image, "filename", ""):
        upload_list.append(image)
    for extra in (images or []):
        if extra and getattr(extra, "filename", ""):
            upload_list.append(extra)
    for idx, f in enumerate(upload_list):
        url = save_upload(f, f"client_{client_id}/products")
        vh = image_avg_hash(str(UPLOAD_DIR / url.replace("/uploads/", "")))
        saved_images.append((url, vh))
    image_url = saved_images[0][0] if saved_images else ""
    vhash = saved_images[0][1] if saved_images else ""
    count = db.query(Product).filter(Product.client_id == client_id).count() + 1
    p = Product(
        client_id=client_id,
        service=service,
        internal_code=f"BOD-{count:06d}",
        barcode=barcode,
        reference=reference,
        name=name,
        brand=brand,
        category=category,
        presentation=presentation,
        image_url=image_url,
        visual_hash=vhash,
        stock=stock,
        min_stock=min_stock,
        real_price=real_price,
        sale_price=sale_price or real_price,
        expiration_date=expiration_date,
        active=True,
        notes=notes,
    )
    db.add(p)
    db.flush()
    for pos, (url, vh) in enumerate(saved_images):
        db.add(ProductImage(product_id=p.id, client_id=client_id, image_url=url, visual_hash=vh, position=pos))
    db.add(StockMovement(client_id=client_id, product_id=p.id, movement_type="CREAR_PRODUCTO", quantity=stock, old_stock=0, new_stock=stock, origin="Registro"))
    sync_product_images(db, p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "product": product_dict(p)}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, payload: dict, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    old_stock = float(p.stock or 0)

    for k in ["name", "brand", "barcode", "reference", "category", "presentation", "real_price", "sale_price", "expiration_date", "notes", "service"]:
        if k in payload:
            setattr(p, k, payload[k])

    for k in ["stock", "min_stock"]:
        if k in payload and payload[k] not in [None, ""]:
            setattr(p, k, float(payload[k] or 0))

    if "active" in payload:
        p.active = bool(payload["active"])

    if "stock" in payload and float(p.stock or 0) != old_stock:
        db.add(StockMovement(
            client_id=p.client_id,
            product_id=p.id,
            movement_type="AJUSTE_MANUAL",
            quantity=float(p.stock or 0) - old_stock,
            old_stock=old_stock,
            new_stock=float(p.stock or 0),
            origin="Edición producto",
            notes="Ajuste directo desde edición de producto"
        ))

    db.commit()
    return {"ok": True, "product": product_dict(p)}

@app.post("/api/stock/adjust")
def adjust_stock(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(int(payload.get("product_id")))
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    qty = float(payload.get("quantity") or 0)
    old = p.stock
    typ = str(payload.get("type") or "").upper()
    if typ == "CARGAR":
        p.stock += qty
    elif typ == "DESCARGAR":
        if qty > p.stock:
            return {"ok": False, "error": "Stock insuficiente"}
        p.stock -= qty
    else:
        return {"ok": False, "error": "Tipo inválido"}
    db.add(StockMovement(client_id=p.client_id, product_id=p.id, movement_type=typ, quantity=qty, old_stock=old, new_stock=p.stock, origin=payload.get("origin", "Manual"), notes=payload.get("notes", "")))
    db.commit()
    return {"ok": True, "product": product_dict(p)}

@app.get("/api/products/search")
def search_product(client_id: int, q: str, db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    ql = (q or "").lower().strip()
    rows = db.query(Product).filter(Product.client_id == client_id, Product.active == True).all()
    matches = []
    for p in rows:
        text = f"{p.id} {p.internal_code} {p.barcode} {p.reference} {p.name} {p.brand} {p.category}".lower()
        if ql in text:
            matches.append(product_dict(p))
    return {"ok": True, "products": matches[:20]}

@app.post("/api/products/detect")
def detect_product(client_id: int = Form(...), image: UploadFile = File(...), db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    captured_url = save_upload(image, f"client_{client_id}/detections")
    captured_path = upload_disk_path(captured_url)
    h = image_avg_hash(str(captured_path)) if captured_path else ""

    candidates = []

    # Limpieza automática: evita comparar contra fotos antiguas ocultas.
    sync_client_products_images(db, client_id)

    refs = db.query(ProductImage).filter(ProductImage.client_id == client_id).order_by(ProductImage.product_id.asc(), ProductImage.position.asc(), ProductImage.id.asc()).all()
    for ref in refs:
        p = db.query(Product).get(ref.product_id)
        if not p or not p.active:
            continue

        # Solo fotos visibles y sincronizadas. Si image_url antigua no está en ProductImage, no participa.
        if not ref.image_url or not upload_disk_path(ref.image_url):
            continue

        ref_sig = ensure_visual_signature(ref, ref.image_url)
        details = visual_match_details(h, ref_sig)
        d = details.get("score")
        if d is not None:
            candidates.append((d, p, ref.image_url, details))

    db.commit()

    # Quitar duplicados por producto, dando más peso a la foto principal.
    # Si la coincidencia viene de la imagen principal del producto, se le da un bonus
    # para que tenga prioridad sobre referencias secundarias parecidas.
    best_by_product = {}
    for score, p, ref_url, details in candidates:
        principal_bonus = float(os.getenv("VISUAL_MAIN_IMAGE_BONUS", "4")) if ref_url == p.image_url else 0.0
        effective_score = max(0.0, float(score) - principal_bonus)

        row = {
            "effective_score": effective_score,
            "raw_score": score,
            "product": p,
            "ref_url": ref_url,
            "details": details,
            "is_main": (ref_url == p.image_url),
        }

        if p.id not in best_by_product or effective_score < best_by_product[p.id]["effective_score"]:
            best_by_product[p.id] = row

    ranked = sorted(best_by_product.values(), key=lambda x: x["effective_score"])

    if ranked:
        best = ranked[0]
        best_score = best["raw_score"]
        best_effective_score = best["effective_score"]
        best_product = best["product"]
        best_ref_url = best["ref_url"]
        best_details = best["details"]
        best_is_main = best["is_main"]

        data = product_dict(best_product)
        data["matched_image_url"] = best_ref_url or best_product.image_url

        suggestions = []
        for item in ranked[:5]:
            sp = item["product"]
            sref = item["ref_url"]
            det = item["details"]
            raw_score = item["raw_score"]
            eff_score = item["effective_score"]
            sd = product_dict(sp)
            sd["matched_image_url"] = sref or sp.image_url
            suggestions.append({
                "score": raw_score,
                "effective_score": eff_score,
                "confidence": max(0, round(100 - float(raw_score), 2)),
                "safe_match": bool(det.get("safe_match")),
                "is_main": bool(item["is_main"]),
                "details": det,
                "product": sd
            })

        support_count = sum(1 for sc, sp, sref, det in candidates if sp.id == best_product.id and det.get("safe_match"))
        nearest_other_score = None
        for item in ranked[1:]:
            if item["product"].id != best_product.id:
                nearest_other_score = item["effective_score"]
                break
        margin_ok = True if nearest_other_score is None else (nearest_other_score - best_effective_score) >= float(os.getenv("VISUAL_MIN_MARGIN", "5"))
        principal_scores = [sc for sc, sp, sref, det in candidates if sp.id == best_product.id and sref == best_product.image_url]
        principal_ok = bool(principal_scores and min(principal_scores) <= float(os.getenv("VISUAL_PRINCIPAL_MAX_SCORE", "40")))
        very_strict = best_score <= float(os.getenv("VISUAL_VERY_STRICT_SCORE", "22"))

        # Reglas duras anti-confusión: botella ≠ botella. Debe coincidir etiqueta/color/letra.
        label_color_ok = bool(best_details.get("good_label_color", False))
        label_text_ok = bool(best_details.get("good_label_text", False))
        center_ok = bool(best_details.get("good_center", False))
        shape_ok = bool(best_details.get("good_shape", False))

        # Más peso a la foto principal:
        # - si la coincidencia viene de la foto principal, basta con match seguro + reglas duras
        # - si viene de una foto secundaria, además se exige apoyo de principal o varias referencias
        accept_product = bool(
            best_details.get("safe_match") and
            label_color_ok and
            (label_text_ok or support_count >= 2) and
            center_ok and shape_ok and
            (
                very_strict or
                principal_ok or
                support_count >= 2 or
                (best_is_main and margin_ok)
            ) and
            (margin_ok or support_count >= 2 or principal_ok)
        )

        if accept_product:
            return {
                "ok": True,
                "captured_image": captured_url,
                "match_score": best_score,
                "effective_match_score": best_effective_score,
                "confidence": max(0, round(100 - float(best_score), 2)),
                "match_distance": best_score,
                "match_details": best_details,
                "support_count": support_count,
                "principal_ok": principal_ok,
                "margin_ok": margin_ok,
                "nearest_other_score": nearest_other_score,
                "matched_on_main_image": best_is_main,
                "similar": True,
                "product": data,
                "suggestions": suggestions
            }

        return {
            "ok": False,
            "captured_image": captured_url,
            "match_score": best_score,
            "effective_match_score": best_effective_score,
            "confidence": max(0, round(100 - float(best_score), 2)),
            "match_distance": best_score,
            "match_details": best_details,
            "support_count": support_count,
            "principal_ok": principal_ok,
            "matched_on_main_image": best_is_main,
            "similar": False,
            "suggestions": suggestions,
            "error": "No hay coincidencia segura. Se parece parcialmente, pero no pasa la validación de etiqueta, color, marca/letras y referencias del mismo producto."
        }

    return {
        "ok": False,
        "captured_image": captured_url,
        "match_score": None,
        "confidence": None,
        "match_distance": None,
        "match_details": {},
        "similar": False,
        "suggestions": [],
        "error": "No hay fotos de referencia suficientes para comparar"
    }

@app.post("/api/products/{product_id}/images")
def upload_product_images(
    product_id: int,
    replace_main: bool = Form(False),
    main_image: UploadFile = File(None),
    images: List[UploadFile] = File(default=[]),
    db=Depends(get_db),
    user=Depends(require_user)
):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    added = []
    if main_image and getattr(main_image, "filename", ""):
        url = save_upload(main_image, f"client_{p.client_id}/products")
        sig = image_avg_hash(str(UPLOAD_DIR / url.replace("/uploads/", "")))
        if replace_main or not p.image_url:
            p.image_url = url
            p.visual_hash = sig
        db.add(ProductImage(product_id=p.id, client_id=p.client_id, image_url=url, visual_hash=sig, position=0))
        added.append(url)

    for f in (images or []):
        if f and getattr(f, "filename", ""):
            url = save_upload(f, f"client_{p.client_id}/products")
            sig = image_avg_hash(str(UPLOAD_DIR / url.replace("/uploads/", "")))
            db.add(ProductImage(product_id=p.id, client_id=p.client_id, image_url=url, visual_hash=sig, position=1))
            added.append(url)

    sync_product_images(db, p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "added": added, "product": product_dict(p)}

@app.post("/api/products/{product_id}/train-from-captured")
def train_product_from_captured(product_id: int, payload: dict, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    image_url = str(payload.get("image_url") or "")
    path = upload_disk_path(image_url)
    if not path:
        return {"ok": False, "error": "Imagen no encontrada para entrenar"}
    sig = image_avg_hash(str(path))
    db.add(ProductImage(product_id=p.id, client_id=p.client_id, image_url=image_url, visual_hash=sig, position=1))
    if not p.image_url:
        p.image_url = image_url
        p.visual_hash = sig
    db.commit()
    return {"ok": True, "product": product_dict(p)}

@app.delete("/api/products/{product_id}/images/{image_id}")
def delete_product_image(product_id: int, image_id: int, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    img = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not img:
        return {"ok": False, "error": "Foto no encontrada"}

    removed_url = img.image_url
    db.delete(img)
    db.flush()

    # Si era la foto principal, se busca otra foto del mismo producto.
    if removed_url and p.image_url == removed_url:
        next_img = db.query(ProductImage).filter(ProductImage.product_id == product_id).order_by(ProductImage.position.asc(), ProductImage.id.asc()).first()
        if next_img:
            p.image_url = next_img.image_url
            p.visual_hash = ensure_visual_signature(next_img, next_img.image_url)
            next_img.position = 0
        else:
            p.image_url = ""
            p.visual_hash = ""

    sync_product_images(db, p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "product": product_dict(p)}

@app.delete("/api/products/{product_id}/images")
def delete_all_product_images(product_id: int, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    db.query(ProductImage).filter(ProductImage.product_id == product_id).delete()
    p.image_url = ""
    p.visual_hash = ""
    sync_product_images(db, p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "product": product_dict(p)}

@app.post("/api/products/{product_id}/sync-images")
def sync_single_product_images(product_id: int, db=Depends(get_db), user=Depends(require_user)):
    p = db.query(Product).get(product_id)
    if not p:
        return {"ok": False, "error": "Producto no encontrado"}
    if user["role"] == "client" and int(user["client_id"]) != p.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    sync_product_images(db, p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "product": product_dict(p)}

# =====================
# SALES / POS
# =====================
@app.post("/api/sales")
def create_sale(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    client_id = int(payload.get("client_id"))
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    items = payload.get("items", [])
    if not items:
        return {"ok": False, "error": "Carrito vacío"}
    sale = Sale(
        client_id=client_id,
        service=payload.get("service", "bodega_pos"),
        customer_name=payload.get("customer_name", "Cliente general"),
        customer_phone=payload.get("customer_phone", ""),
        discount=float(payload.get("discount") or 0),
        payment_method=payload.get("payment_method", "Efectivo"),
        status="PAGADO",
        ticket_token=uuid.uuid4().hex
    )
    db.add(sale)
    db.flush()
    subtotal = 0
    for it in items:
        product_id = it.get("product_id")
        qty = float(it.get("quantity") or 1)
        if product_id:
            p = db.query(Product).get(int(product_id))
            if not p:
                continue
            if qty > p.stock:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente: {p.name}")
            unit = float(it.get("unit_price") or p.sale_price)
            product_name = product_display_name(p)
            old = p.stock
            p.stock -= qty
            db.add(StockMovement(client_id=client_id, product_id=p.id, movement_type="DESCARGAR", quantity=qty, old_stock=old, new_stock=p.stock, origin="POS venta"))
        else:
            unit = float(it.get("unit_price") or 0)
            product_name = it.get("product_name", "Producto manual")
        total = qty * unit
        subtotal += total
        db.add(SaleItem(sale_id=sale.id, client_id=client_id, product_id=product_id, product_name=product_name, quantity=qty, unit_price=unit, total=total))
    sale.subtotal = subtotal
    sale.total = max(0, subtotal - sale.discount)
    db.commit()
    return {
        "ok": True, "sale_id": sale.id, "total": sale.total,
        "ticket_url": public_url(f"/public/sale/{sale.ticket_token}"),
        "pdf_url": public_url(f"/api/sales/{sale.ticket_token}/pdf")
    }

def get_sale_bundle(db, token):
    sale = db.query(Sale).filter(Sale.ticket_token == token).first()
    if not sale:
        return None, None, []
    client = db.query(Client).get(sale.client_id)
    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
    return sale, client, items

@app.get("/public/sale/{token}", response_class=HTMLResponse)
def public_sale_ticket(token: str, db=Depends(get_db)):
    sale, client, items = get_sale_bundle(db, token)
    if not sale:
        return HTMLResponse("<h1>Ticket no encontrado</h1>", status_code=404)
    d = client.design if client else None
    logo = d.logo_url if d else ""
    rows = "".join([f"<tr><td>{i.product_name}</td><td>{i.quantity:g}</td><td>{money(i.unit_price)}</td><td>{money(i.total)}</td></tr>" for i in items])
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Ticket venta</title><style>
    body{{font-family:Arial;background:#f4f7fb;margin:0;padding:20px;color:#111827}}
    .ticket{{max-width:520px;margin:auto;background:white;border-radius:22px;padding:24px;box-shadow:0 10px 30px #0001}}
    .logo{{max-width:120px;max-height:80px}} h1{{margin:8px 0}} table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left}}
    .total{{font-size:34px;color:#00A6A6;font-weight:900}} .pill{{background:#e8f8f8;padding:8px 12px;border-radius:999px;display:inline-block}}
    </style></head><body><div class="ticket">
    {'<img class="logo" src="'+logo+'">' if logo else ''}
    <h1>{client.business_name if client else 'Bodetronic'}</h1>
    <p>{client.address if client else ''}</p>
    <p class="pill">Venta #{sale.id} | {peru_time_text(sale.created_at)}</p>
    <h2>Cliente: {sale.customer_name}</h2>
    <p>Celular/WhatsApp: {sale.customer_phone or "-"}</p>
    <table><thead><tr><th>Producto</th><th>Cant.</th><th>P. unit.</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
    <p>Subtotal: <b>{money(sale.subtotal)}</b></p>
    <p>Descuento: <b>{money(sale.discount)}</b></p>
    <div class="total">Total: {money(sale.total)}</div>
    <p>Método de pago: <b>{sale.payment_method}</b></p>
    <p>Gracias por su compra.</p>
    </div></body></html>
    """

@app.get("/api/sales/{token}/pdf")
def sale_pdf(token: str, db=Depends(get_db)):
    sale, client, items = get_sale_bundle(db, token)
    if not sale:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 760
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, client.business_name if client else "Bodetronic")
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Ticket venta #{sale.id} - {peru_time_text(sale.created_at)}")
    y -= 20
    c.drawString(50, y, f"Cliente: {sale.customer_name}")
    y -= 18
    c.drawString(50, y, f"WhatsApp: {sale.customer_phone or '-'}")
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Producto")
    c.drawString(260, y, "Cant.")
    c.drawString(330, y, "P. unit.")
    c.drawString(430, y, "Total")
    y -= 15
    c.setFont("Helvetica", 10)
    for i in items:
        c.drawString(50, y, (i.product_name or "")[:34])
        c.drawString(260, y, f"{i.quantity:g}")
        c.drawString(330, y, money(i.unit_price))
        c.drawString(430, y, money(i.total))
        y -= 18
        if y < 80:
            c.showPage()
            y = 760
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Subtotal: {money(sale.subtotal)}")
    y -= 20
    c.drawString(50, y, f"Descuento: {money(sale.discount)}")
    y -= 25
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, f"TOTAL: {money(sale.total)}")
    y -= 28
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Método de pago: {sale.payment_method}")
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=ticket_venta_{sale.id}.pdf"})

# =====================
# CREDITS
# =====================
@app.get("/api/credits/customers")
def list_credit_customers(client_id: int, db=Depends(get_db), user=Depends(require_user)):
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = db.query(CreditCustomer).filter(CreditCustomer.client_id == client_id, CreditCustomer.active == True).order_by(CreditCustomer.id.desc()).all()
    return {"ok": True, "customers": [{"id": c.id, "name": c.name, "whatsapp": c.whatsapp, "total_current": c.total_current, "public_url": public_url(f"/public/credit/{c.public_token}")} for c in rows]}

@app.post("/api/credits/customers")
def create_credit_customer(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    client_id = int(payload.get("client_id"))
    if user["role"] == "client" and int(user["client_id"]) != client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    cc = CreditCustomer(client_id=client_id, name=payload.get("name", ""), whatsapp=payload.get("whatsapp", ""), public_token=uuid.uuid4().hex, notes=payload.get("notes", ""))
    db.add(cc)
    db.commit()
    return {"ok": True, "customer_id": cc.id, "public_url": public_url(f"/public/credit/{cc.public_token}")}


@app.delete("/api/credits/customers/{customer_id}")
def delete_credit_customer(customer_id: int, db=Depends(get_db), user=Depends(require_user)):
    cc = db.query(CreditCustomer).get(customer_id)
    if not cc:
        return {"ok": False, "error": "Cuenta no encontrada"}
    if user["role"] == "client" and int(user["client_id"]) != cc.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    # Borrado lógico para no perder historial ni comprobantes.
    cc.active = False
    db.commit()
    return {"ok": True}

@app.get("/api/credits/{customer_id}")
def credit_detail(customer_id: int, db=Depends(get_db), user=Depends(require_user)):
    cc = db.query(CreditCustomer).get(customer_id)
    if not cc:
        return {"ok": False, "error": "Cuenta no encontrada"}
    if user["role"] == "client" and int(user["client_id"]) != cc.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    items = db.query(CreditItem).filter(CreditItem.credit_customer_id == cc.id, CreditItem.status == "PENDIENTE").order_by(CreditItem.id.desc()).all()
    history = db.query(CreditPayment).filter(CreditPayment.credit_customer_id == cc.id).order_by(CreditPayment.id.desc()).all()
    return {"ok": True, "customer": {"id": cc.id, "name": cc.name, "whatsapp": cc.whatsapp, "total_current": cc.total_current, "public_url": public_url(f"/public/credit/{cc.public_token}"), "pdf_url": public_url(f"/public/credit/{cc.public_token}/pdf")},
            "items": [{"id": i.id, "product_name": i.product_name, "quantity": i.quantity, "unit_price": i.unit_price, "total": i.total, "picked_by": i.picked_by, "created_at": peru_time_text(i.created_at)} for i in items],
            "history": [{"id": h.id, "total_paid": h.total_paid, "created_at": peru_time_text(h.created_at), "public_url": public_url(f"/public/credit-paid/{h.public_token}"), "pdf_url": public_url(f"/public/credit-paid/{h.public_token}/pdf")} for h in history]}

@app.post("/api/credits/items")
def add_credit_item(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    cc = db.query(CreditCustomer).get(int(payload.get("credit_customer_id")))
    if not cc:
        return {"ok": False, "error": "Cuenta no encontrada"}
    if user["role"] == "client" and int(user["client_id"]) != cc.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    p = None
    if payload.get("product_id"):
        p = db.query(Product).get(int(payload.get("product_id")))
    qty = float(payload.get("quantity") or 1)
    product_name = payload.get("product_name") or (product_display_name(p) if p else "Producto manual")
    if p:
        product_name = product_display_name(p)
    unit = float(payload.get("unit_price") or (p.sale_price if p else 0))
    total = qty * unit
    if p:
        if qty > p.stock:
            return {"ok": False, "error": "Stock insuficiente"}
        old = p.stock
        p.stock -= qty
        db.add(StockMovement(client_id=cc.client_id, product_id=p.id, movement_type="DESCARGAR", quantity=qty, old_stock=old, new_stock=p.stock, origin="Crédito/Fiado"))
    item = CreditItem(credit_customer_id=cc.id, client_id=cc.client_id, product_id=p.id if p else None, product_name=product_name, quantity=qty, unit_price=unit, total=total, picked_by=payload.get("picked_by", ""), notes=payload.get("notes", ""))
    cc.total_current += total
    db.add(item)
    db.commit()
    return {"ok": True, "item_id": item.id, "total_current": cc.total_current}

@app.post("/api/credits/{customer_id}/pay")
def pay_credit(customer_id: int, db=Depends(get_db), user=Depends(require_user)):
    cc = db.query(CreditCustomer).get(customer_id)
    if not cc:
        return {"ok": False, "error": "Cuenta no encontrada"}
    if user["role"] == "client" and int(user["client_id"]) != cc.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    items = db.query(CreditItem).filter(CreditItem.credit_customer_id == cc.id, CreditItem.status == "PENDIENTE").all()
    if not items:
        return {"ok": False, "error": "No hay deuda pendiente"}
    detail = [{"product_name": i.product_name, "quantity": i.quantity, "unit_price": i.unit_price, "total": i.total, "created_at": peru_time_text(i.created_at)} for i in items]
    total = sum(i.total for i in items)
    for i in items:
        i.status = "PAGADO"
    pay = CreditPayment(credit_customer_id=cc.id, client_id=cc.client_id, total_paid=total, detail_json=json.dumps(detail, ensure_ascii=False), public_token=uuid.uuid4().hex)
    db.add(pay)
    cc.total_current = 0
    db.commit()
    return {"ok": True, "total": total, "paid_url": public_url(f"/public/credit-paid/{pay.public_token}"), "paid_pdf_url": public_url(f"/public/credit-paid/{pay.public_token}/pdf")}

def credit_html_bundle(db, cc: CreditCustomer, items, status="PENDIENTE"):
    client = db.query(Client).get(cc.client_id)
    rows = "".join([f"<tr><td>{i.product_name}</td><td>{i.quantity:g}</td><td>{money(i.unit_price)}</td><td>{money(i.total)}</td><td>{peru_time_text(i.created_at)}</td></tr>" for i in items])
    total = sum([i.total for i in items])
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Crédito {cc.name}</title><style>
    body{{font-family:Arial;background:#f4f7fb;margin:0;padding:20px;color:#111827}}.ticket{{max-width:650px;margin:auto;background:white;border-radius:22px;padding:24px;box-shadow:0 10px 30px #0001}}
    table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left}}.total{{font-size:36px;color:#00A6A6;font-weight:900}}.badge{{display:inline-block;padding:8px 12px;background:#ecfeff;border-radius:999px}}
    </style></head><body><div class="ticket">
    <h1>{client.business_name if client else 'Bodetronic'}</h1>
    <p class="badge">Estado: {status}</p>
    <h2>Cliente: {cc.name}</h2>
    <p>WhatsApp: {cc.whatsapp}</p>
    <div class="total">Total: {money(total)}</div>
    <table><thead><tr><th>Producto</th><th>Cant.</th><th>P. unit.</th><th>Total</th><th>Fecha</th></tr></thead><tbody>{rows}</tbody></table>
    <p>Este enlace muestra solo el detalle de esta cuenta.</p>
    </div></body></html>
    """

@app.get("/public/credit/{token}", response_class=HTMLResponse)
def public_credit(token: str, db=Depends(get_db)):
    cc = db.query(CreditCustomer).filter(CreditCustomer.public_token == token).first()
    if not cc:
        return HTMLResponse("<h1>Crédito no encontrado</h1>", status_code=404)
    items = db.query(CreditItem).filter(CreditItem.credit_customer_id == cc.id, CreditItem.status == "PENDIENTE").order_by(CreditItem.id.asc()).all()
    return credit_html_bundle(db, cc, items, "PENDIENTE")

@app.get("/public/credit/{token}/pdf")
def public_credit_pdf(token: str, db=Depends(get_db)):
    cc = db.query(CreditCustomer).filter(CreditCustomer.public_token == token).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    items = db.query(CreditItem).filter(CreditItem.credit_customer_id == cc.id, CreditItem.status == "PENDIENTE").order_by(CreditItem.id.asc()).all()
    return build_credit_pdf(db, cc, items, "PENDIENTE")

@app.get("/public/credit-paid/{token}", response_class=HTMLResponse)
def public_credit_paid(token: str, db=Depends(get_db)):
    pay = db.query(CreditPayment).filter(CreditPayment.public_token == token).first()
    if not pay:
        return HTMLResponse("<h1>Comprobante no encontrado</h1>", status_code=404)
    cc = db.query(CreditCustomer).get(pay.credit_customer_id)
    data = json.loads(pay.detail_json or "[]")
    fake_items = []
    for x in data:
        obj = type("Item", (), {})()
        obj.product_name = x.get("product_name")
        obj.quantity = x.get("quantity")
        obj.unit_price = x.get("unit_price")
        obj.total = x.get("total")
        obj.created_at = pay.created_at
        fake_items.append(obj)
    return credit_html_bundle(db, cc, fake_items, "PAGADO")

@app.get("/public/credit-paid/{token}/pdf")
def public_credit_paid_pdf(token: str, db=Depends(get_db)):
    pay = db.query(CreditPayment).filter(CreditPayment.public_token == token).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    cc = db.query(CreditCustomer).get(pay.credit_customer_id)
    data = json.loads(pay.detail_json or "[]")
    fake_items = []
    for x in data:
        obj = type("Item", (), {})()
        obj.product_name = x.get("product_name")
        obj.quantity = x.get("quantity")
        obj.unit_price = x.get("unit_price")
        obj.total = x.get("total")
        obj.created_at = pay.created_at
        fake_items.append(obj)
    return build_credit_pdf(db, cc, fake_items, "PAGADO")

@app.get("/api/credits/{customer_id}/pdf")
def credit_pdf(customer_id: int, db=Depends(get_db), user=Depends(require_user)):
    cc = db.query(CreditCustomer).get(customer_id)
    if not cc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if user["role"] == "client" and int(user["client_id"]) != cc.client_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    items = db.query(CreditItem).filter(CreditItem.credit_customer_id == cc.id, CreditItem.status == "PENDIENTE").order_by(CreditItem.id.asc()).all()
    return build_credit_pdf(db, cc, items, "PENDIENTE")

def build_credit_pdf(db, cc, items, status):
    client = db.query(Client).get(cc.client_id)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 760
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, client.business_name if client else "Bodetronic")
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Crédito/Cuenta - {status} - {peru_time_text()}")
    y -= 20
    c.drawString(50, y, f"Cliente: {cc.name} | WhatsApp: {cc.whatsapp}")
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Producto")
    c.drawString(250, y, "Cant.")
    c.drawString(310, y, "P. unit.")
    c.drawString(400, y, "Total")
    y -= 15
    total = 0
    c.setFont("Helvetica", 10)
    for i in items:
        total += i.total
        c.drawString(50, y, (i.product_name or "")[:32])
        c.drawString(250, y, f"{i.quantity:g}")
        c.drawString(310, y, money(i.unit_price))
        c.drawString(400, y, money(i.total))
        y -= 18
        if y < 80:
            c.showPage()
            y = 760
    y -= 15
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, f"TOTAL: {money(total)}")
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=credito_{cc.id}.pdf"})

# =====================
# AUTOMATION / REMINDERS
# =====================
@app.get("/api/automation/settings")
def get_automation_settings(db=Depends(get_db), user=Depends(require_admin)):
    rows = db.query(AutomationSetting).all()
    return {"ok": True, "settings": {r.key: r.value for r in rows}}

@app.put("/api/automation/settings")
def update_automation_settings(payload: dict, db=Depends(get_db), user=Depends(require_admin)):
    for k, v in payload.items():
        set_setting(db, k, v)
    return {"ok": True}

@app.post("/api/reminders/send")
def send_reminder(payload: dict, db=Depends(get_db), user=Depends(require_user)):
    channel = payload.get("channel", "whatsapp")
    webhook = setting(db, "whatsapp_webhook" if channel in ["whatsapp", "ambos"] else "email_webhook")
    result = call_webhook(webhook, payload)
    db.add(ReminderLog(client_id=payload.get("client_id"), channel=channel, destination=payload.get("destination", ""), message=payload.get("message", ""), result=json.dumps(result, ensure_ascii=False)))
    db.commit()
    return {"ok": True, "result": result}

@app.get("/api/health")
def health():
    return {"ok": True, "app": APP_NAME, "time": peru_time_text()}
