import os, sqlite3, json, time, hmac, hashlib, base64, uuid, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import imagehash, requests

DB=os.getenv('DATABASE_PATH','bodetronic.db')
SECRET=os.getenv('SECRET_KEY','cambia-esta-clave')
MASTER_USER=os.getenv('MASTER_USER','73221820')
MASTER_PASS=os.getenv('MASTER_PASS','jdiazg20')
UPLOAD=Path('uploads'); UPLOAD.mkdir(exist_ok=True)
app=FastAPI(title='Bodetronic Python Pro')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')

def con():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def rows(sql,args=()):
    c=con(); r=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close(); return r

def one(sql,args=()):
    r=rows(sql,args); return r[0] if r else None

def run(sql,args=()):
    c=con(); cur=c.execute(sql,args); c.commit(); i=cur.lastrowid; c.close(); return i

def hp(p): return hashlib.sha256(('bt-'+str(p)).encode()).hexdigest()

def tok(d):
    d=dict(d); d['exp']=int(time.time())+259200
    b=base64.urlsafe_b64encode(json.dumps(d,separators=(',',':')).encode()).decode().rstrip('=')
    s=hmac.new(SECRET.encode(),b.encode(),hashlib.sha256).hexdigest(); return b+'.'+s

def untok(t):
    try:
        b,s=t.split('.',1); good=hmac.new(SECRET.encode(),b.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(s,good): return None
        d=json.loads(base64.urlsafe_b64decode(b+'='*(-len(b)%4)))
        return d if d.get('exp',0)>time.time() else None
    except Exception: return None

def auth(authorization: str = Header(default='')):
    u=untok(authorization.replace('Bearer','').strip())
    if not u: raise HTTPException(401,'Token invalido')
    return u

def adm(authorization: str = Header(default='')):
    u=auth(authorization)
    if u.get('role')!='admin': raise HTTPException(403,'Solo admin')
    return u

def setup_db():
    c=con(); c.executescript('''
    CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,name TEXT,username TEXT UNIQUE,password TEXT,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY,business_name TEXT,owner_name TEXT,dni_ruc TEXT,whatsapp TEXT,email TEXT,status TEXT DEFAULT 'ACTIVO',membership TEXT DEFAULT 'Demo',expires_at TEXT DEFAULT 'INDEFINIDO',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS access(id INTEGER PRIMARY KEY,client_id INTEGER,username TEXT UNIQUE,password TEXT,raw_hint TEXT,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY,client_id INTEGER UNIQUE,bodega INTEGER DEFAULT 0,pos INTEGER DEFAULT 0,credits INTEGER DEFAULT 0,exp INTEGER DEFAULT 0,minimarket INTEGER DEFAULT 0,almacen INTEGER DEFAULT 0,picking INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS design(id INTEGER PRIMARY KEY,client_id INTEGER UNIQUE,logo_url TEXT,title TEXT,primary_color TEXT DEFAULT '#00A6A6',secondary_color TEXT DEFAULT '#0F172A',banner_text TEXT,sponsor_text TEXT,visible_info TEXT);
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,client_id INTEGER,label TEXT,method TEXT,holder_name TEXT,phone TEXT,qr_url TEXT,message TEXT,active INTEGER DEFAULT 1,position INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY,client_id INTEGER,title TEXT,media_url TEXT,media_type TEXT,location TEXT,sponsor_name TEXT,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,client_id INTEGER,internal_code TEXT,barcode TEXT,name TEXT,brand TEXT,category TEXT,image_url TEXT,visual_hash TEXT,stock REAL DEFAULT 0,real_price REAL DEFAULT 0,sale_price REAL DEFAULT 0,expiration_date TEXT,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY,client_id INTEGER,product_id INTEGER,type TEXT,quantity REAL,old_stock REAL,new_stock REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,client_id INTEGER,total REAL,status TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY,sale_id INTEGER,product_id INTEGER,product_name TEXT,quantity REAL,unit_price REAL,total REAL);
    CREATE TABLE IF NOT EXISTS credit_customers(id INTEGER PRIMARY KEY,client_id INTEGER,name TEXT,whatsapp TEXT,total_current REAL DEFAULT 0,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS credit_items(id INTEGER PRIMARY KEY,credit_customer_id INTEGER,client_id INTEGER,product_id INTEGER,product_name TEXT,quantity REAL,unit_price REAL,total REAL,picked_by TEXT,status TEXT DEFAULT 'PENDIENTE',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS n8n(id INTEGER PRIMARY KEY,key TEXT UNIQUE,value TEXT);
    '''); c.commit(); c.close()
    if not one('SELECT * FROM admins WHERE username=?',(MASTER_USER,)):
        run('INSERT INTO admins(name,username,password,active) VALUES(?,?,?,1)',('Jorge Diaz',MASTER_USER,hp(MASTER_PASS)))
    for k,v in {'visual_ai_webhook':'','whatsapp_webhook':'','email_webhook':'','tpl_whatsapp':'Hola {{cliente}}, {{detalle}} Total S/ {{total}}'}.items():
        if not one('SELECT * FROM n8n WHERE key=?',(k,)): run('INSERT INTO n8n(key,value) VALUES(?,?)',(k,v))

@app.on_event('startup')
def startup(): setup_db()

@app.get('/', response_class=HTMLResponse)
def home(): return FileResponse('static/index.html')

@app.post('/api/auth/login')
def login(p:dict):
    setup_db(); u=str(p.get('username','')).strip(); pw=str(p.get('password','')).strip()
    a=one('SELECT * FROM admins WHERE username=? AND active=1',(u,))
    if a and a['password']==hp(pw): return {'ok':True,'role':'admin','token':tok({'role':'admin','id':a['id']})}
    ac=one('SELECT * FROM access WHERE username=? AND active=1',(u,))
    if ac and ac['password']==hp(pw):
        c=one('SELECT * FROM clients WHERE id=?',(ac['client_id'],))
        if not c or c['status']!='ACTIVO': return {'ok':False,'error':'Cliente sin acceso activo'}
        return {'ok':True,'role':'client','token':tok({'role':'client','client_id':c['id']}),'client':c}
    return {'ok':False,'error':'Credenciales incorrectas'}

@app.get('/api/admin/data')
def admin_data(authorization: str = Header(default='')):
    adm(authorization); clients=rows('SELECT * FROM clients ORDER BY id DESC')
    for c in clients:
        c['access']=one('SELECT username,raw_hint,active FROM access WHERE client_id=?',(c['id'],)) or {}
        c['services']=one('SELECT * FROM services WHERE client_id=?',(c['id'],)) or {}
        c['design']=one('SELECT * FROM design WHERE client_id=?',(c['id'],)) or {}
        c['payments']=rows('SELECT * FROM payments WHERE client_id=?',(c['id'],))
    return {'ok':True,'clients':clients,'stats':{'clients':len([c for c in clients if c['status']=='ACTIVO']),'products':len(rows('SELECT id FROM products WHERE active=1')),'sales':len(rows('SELECT id FROM sales'))}}

@app.post('/api/admin/clients')
def create_client(p:dict,authorization: str = Header(default='')):
    adm(authorization); business=p.get('business_name'); dni=str(p.get('dni_ruc',''))
    if not business or not dni: return {'ok':False,'error':'Completa negocio y DNI/RUC'}
    username=p.get('username') or ''.join(ch for ch in business.lower() if ch.isalnum())[:18] or 'cliente'; raw=p.get('password') or dni
    cid=run('INSERT INTO clients(business_name,owner_name,dni_ruc,whatsapp,email,status,membership,expires_at) VALUES(?,?,?,?,?,?,?,?)',(business,p.get('owner_name',''),dni,p.get('whatsapp',''),p.get('email',''),'ACTIVO',p.get('membership','Demo'),p.get('expires_at','INDEFINIDO')))
    run('INSERT INTO access(client_id,username,password,raw_hint,active) VALUES(?,?,?,?,1)',(cid,username,hp(raw),raw))
    s=p.get('services',{})
    run('INSERT INTO services(client_id,bodega,pos,credits,exp,minimarket,almacen,picking) VALUES(?,?,?,?,?,?,?,?)',(cid,int(bool(s.get('bodega'))),int(bool(s.get('pos'))),int(bool(s.get('credits'))),int(bool(s.get('exp'))),int(bool(s.get('minimarket'))),int(bool(s.get('almacen'))),int(bool(s.get('picking')))))
    run('INSERT INTO design(client_id,title) VALUES(?,?)',(cid,business)); run('INSERT INTO payments(client_id,label,method,holder_name,phone,message,active) VALUES(?,?,?,?,?,?,1)',(cid,'Principal','Yape',business,p.get('whatsapp',''),'Realiza tu pago'))
    return {'ok':True,'client_id':cid,'username':username,'password':raw}

@app.put('/api/admin/clients/{cid}/design')
def save_design(cid:int,p:dict,authorization: str = Header(default='')):
    adm(authorization); run('UPDATE design SET logo_url=?,title=?,primary_color=?,secondary_color=?,banner_text=?,sponsor_text=?,visible_info=? WHERE client_id=?',(p.get('logo_url',''),p.get('title',''),p.get('primary_color','#00A6A6'),p.get('secondary_color','#0F172A'),p.get('banner_text',''),p.get('sponsor_text',''),p.get('visible_info',''),cid)); return {'ok':True}

@app.put('/api/admin/clients/{cid}/services')
def save_services(cid:int,p:dict,authorization: str = Header(default='')):
    adm(authorization); run('UPDATE services SET bodega=?,pos=?,credits=?,exp=?,minimarket=?,almacen=?,picking=? WHERE client_id=?',(int(bool(p.get('bodega'))),int(bool(p.get('pos'))),int(bool(p.get('credits'))),int(bool(p.get('exp'))),int(bool(p.get('minimarket'))),int(bool(p.get('almacen'))),int(bool(p.get('picking'))),cid)); return {'ok':True}

@app.post('/api/admin/ads')
def add_ad(p:dict,authorization: str = Header(default='')):
    adm(authorization); run('INSERT INTO ads(client_id,title,media_url,media_type,location,sponsor_name,active) VALUES(?,?,?,?,?,?,1)',(p.get('client_id'),p.get('title',''),p.get('media_url',''),p.get('media_type','image'),p.get('location','home'),p.get('sponsor_name',''))); return {'ok':True}

@app.post('/api/admin/clients/{cid}/payments')
def add_pay(cid:int,p:dict,authorization: str = Header(default='')):
    adm(authorization); run('INSERT INTO payments(client_id,label,method,holder_name,phone,qr_url,message,active,position) VALUES(?,?,?,?,?,?,?,?,?)',(cid,p.get('label',''),p.get('method','Yape'),p.get('holder_name',''),p.get('phone',''),p.get('qr_url',''),p.get('message',''),1,int(p.get('position',0)))); return {'ok':True}

@app.get('/api/client/bundle')
def bundle(authorization: str = Header(default='')):
    u=auth(authorization); cid=u.get('client_id'); return {'ok':True,'client':one('SELECT * FROM clients WHERE id=?',(cid,)),'services':one('SELECT * FROM services WHERE client_id=?',(cid,)) or {},'design':one('SELECT * FROM design WHERE client_id=?',(cid,)) or {},'payments':rows('SELECT * FROM payments WHERE client_id=? AND active=1',(cid,)),'products':rows('SELECT * FROM products WHERE client_id=? AND active=1',(cid,)),'credits':rows('SELECT * FROM credit_customers WHERE client_id=? AND active=1',(cid,)),'ads':rows('SELECT * FROM ads WHERE active=1 AND (client_id IS NULL OR client_id=?)',(cid,))}

def save_file(file,folder):
    d=UPLOAD/folder; d.mkdir(parents=True,exist_ok=True); name=uuid.uuid4().hex+'_'+(file.filename or 'file'); path=d/name
    with path.open('wb') as f: shutil.copyfileobj(file.file,f)
    return '/uploads/'+folder+'/'+name, str(path)

def ih(path):
    try: return str(imagehash.phash(Image.open(path).convert('RGB')))
    except Exception: return ''

@app.post('/api/products')
def product(client_id:int=Form(...),name:str=Form(...),brand:str=Form(''),barcode:str=Form(''),stock:float=Form(0),real_price:float=Form(0),sale_price:float=Form(0),expiration_date:str=Form(''),image:UploadFile=File(None),authorization: str = Header(default='')):
    auth(authorization); url=''; h=''
    if image: url,path=save_file(image,f'client_{client_id}/products'); h=ih(path)
    count=len(rows('SELECT id FROM products WHERE client_id=?',(client_id,)))+1; final=sale_price or round(real_price*1.3,2)
    pid=run('INSERT INTO products(client_id,internal_code,barcode,name,brand,image_url,visual_hash,stock,real_price,sale_price,expiration_date,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)',(client_id,f'BOD-{count:06d}',barcode,name,brand,url,h,stock,real_price,final,expiration_date)); return {'ok':True,'product_id':pid}

@app.get('/api/products/search')
def search(client_id:int,q:str,authorization: str = Header(default='')):
    auth(authorization); term=q.lower()
    for p in rows('SELECT * FROM products WHERE client_id=? AND active=1',(client_id,)):
        if term in str(p['id']).lower() or term in str(p['internal_code']).lower() or term in str(p['barcode']).lower() or term in str(p['name']).lower() or term in str(p['brand']).lower(): return {'ok':True,'product':p}
    return {'ok':False,'error':'Producto no encontrado'}

@app.post('/api/products/detect')
def detect(client_id:int=Form(...),image:UploadFile=File(...),authorization: str = Header(default='')):
    auth(authorization); url,path=save_file(image,f'client_{client_id}/detections'); h=ih(path); best=None; bd=999
    for p in rows('SELECT * FROM products WHERE client_id=? AND active=1 AND visual_hash<>""',(client_id,)):
        try: d=imagehash.hex_to_hash(h)-imagehash.hex_to_hash(p['visual_hash'])
        except Exception: d=999
        if d<bd: best=p; bd=d
    return {'ok':bool(best and bd<=12),'captured_image':url,'match_score':bd if best else None,'product':best,'error':'' if best and bd<=12 else 'No se encontro similar'}

@app.post('/api/stock/adjust')
def stock(p:dict,authorization: str = Header(default='')):
    auth(authorization); prod=one('SELECT * FROM products WHERE id=?',(p.get('product_id'),)); qty=float(p.get('quantity',0)); old=float(prod['stock']); typ=p.get('type','').upper(); new=old+qty if typ=='CARGAR' else old-qty
    if typ=='DESCARGAR' and qty>old: return {'ok':False,'error':'Stock insuficiente'}
    run('UPDATE products SET stock=? WHERE id=?',(new,prod['id'])); run('INSERT INTO stock(client_id,product_id,type,quantity,old_stock,new_stock) VALUES(?,?,?,?,?,?)',(prod['client_id'],prod['id'],typ,qty,old,new)); return {'ok':True,'stock':new}

@app.post('/api/sales')
def sale(p:dict,authorization: str = Header(default='')):
    auth(authorization); items=p.get('items',[]); sid=run('INSERT INTO sales(client_id,total,status) VALUES(?,?,?)',(p.get('client_id'),0,'PAGADO')); total=0
    for it in items:
        prod=one('SELECT * FROM products WHERE id=?',(it.get('product_id'),)); qty=float(it.get('quantity',1)); sub=qty*float(prod['sale_price']); total+=sub; run('INSERT INTO sale_items(sale_id,product_id,product_name,quantity,unit_price,total) VALUES(?,?,?,?,?,?)',(sid,prod['id'],prod['name'],qty,prod['sale_price'],sub)); run('UPDATE products SET stock=? WHERE id=?',(float(prod['stock'])-qty,prod['id']))
    run('UPDATE sales SET total=? WHERE id=?',(total,sid)); return {'ok':True,'sale_id':sid,'total':total}

@app.get('/api/credits/customers')
def credits(client_id:int,authorization: str = Header(default='')):
    auth(authorization); return {'ok':True,'customers':rows('SELECT * FROM credit_customers WHERE client_id=? AND active=1',(client_id,))}
@app.post('/api/credits/customers')
def new_credit(p:dict,authorization: str = Header(default='')):
    auth(authorization); cid=run('INSERT INTO credit_customers(client_id,name,whatsapp,total_current,active) VALUES(?,?,?,?,1)',(p.get('client_id'),p.get('name'),p.get('whatsapp',''),0)); return {'ok':True,'id':cid}
@app.get('/api/credits/{cid}')
def credit(cid:int,authorization: str = Header(default='')):
    auth(authorization); c=one('SELECT * FROM credit_customers WHERE id=?',(cid,)); items=rows('SELECT * FROM credit_items WHERE credit_customer_id=? AND status="PENDIENTE"',(cid,)); total=sum(float(i['total']) for i in items); run('UPDATE credit_customers SET total_current=? WHERE id=?',(total,cid)); return {'ok':True,'customer':c,'items':items,'total':total}
@app.post('/api/credits/items')
def add_credit(p:dict,authorization: str = Header(default='')):
    auth(authorization); prod=one('SELECT * FROM products WHERE id=?',(p.get('product_id'),)) if p.get('product_id') else None; name=p.get('product_name') or (prod['name'] if prod else ''); price=float(p.get('unit_price') or (prod['sale_price'] if prod else 0)); qty=float(p.get('quantity',1)); total=qty*price; run('INSERT INTO credit_items(credit_customer_id,client_id,product_id,product_name,quantity,unit_price,total,picked_by,status) VALUES(?,?,?,?,?,?,?,?,?)',(p.get('credit_customer_id'),p.get('client_id'),p.get('product_id'),name,qty,price,total,p.get('picked_by',''),'PENDIENTE')); return {'ok':True,'total':total}
@app.post('/api/credits/{cid}/pay')
def pay(cid:int,authorization: str = Header(default='')):
    auth(authorization); items=rows('SELECT * FROM credit_items WHERE credit_customer_id=? AND status="PENDIENTE"',(cid,)); total=sum(float(i['total']) for i in items); run('UPDATE credit_items SET status="PAGADO" WHERE credit_customer_id=?',(cid,)); run('UPDATE credit_customers SET total_current=0 WHERE id=?',(cid,)); return {'ok':True,'total':total}
