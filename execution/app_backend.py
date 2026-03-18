import os
import sqlite3
import uuid
from datetime import date, datetime
import io
import zipfile
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

import sys
# Add current directory to path so internal modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import existing rendering logic
from render_invoice import InvoiceRenderer, fetch_invoice_data, generate_pdf

app = FastAPI(title="Professional GST Invoice API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoices.db")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
FAVICONS_DIR = os.path.join(UPLOADS_DIR, "favicons")

# Ensure upload directories exist
os.makedirs(FAVICONS_DIR, exist_ok=True)

# --- Pydantic Models ---

class CompanyProfile(BaseModel):
    id: Optional[str] = None
    name: str
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state_name: Optional[str] = None
    state_code: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    place_id: Optional[str] = None
    gstin: Optional[str] = None
    pan_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_address: Optional[str] = None
    declaration_text: Optional[str] = None
    terms_conditions: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    landline: Optional[str] = None
    fax: Optional[str] = None
    is_default: bool = False
    favicon_url: Optional[str] = None

class Client(BaseModel):
    id: Optional[str] = None
    name: str
    billing_address_line_1: Optional[str] = None
    billing_address_line_2: Optional[str] = None
    city: Optional[str] = None
    state_name: Optional[str] = None
    state_code: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    place_id: Optional[str] = None
    gstin: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    landline: Optional[str] = None
    fax: Optional[str] = None

class ShippingAddress(BaseModel):
    id: Optional[str] = None
    client_id: str
    branch_name: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state_name: Optional[str] = None
    state_code: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    place_id: Optional[str] = None
    gstin: Optional[str] = None

class ItemMaster(BaseModel):
    id: Optional[str] = None
    description: str
    hsn_sac: Optional[str] = None
    default_unit: Optional[str] = "NOS"
    gst_rate: float = 18.0

class InvoiceItem(BaseModel):
    item_id: Optional[str] = None
    description: str
    hsn_sac: Optional[str] = None
    quantity: float
    unit: str
    rate: float
    taxable_value: float
    cgst_rate: float = 0
    sgst_rate: float = 0
    igst_rate: float = 0
    tax_amount: float
    total_amount: float

class InvoiceCreate(BaseModel):
    client_id: str
    shipping_id: Optional[str] = None
    invoice_no: str
    invoice_date: Optional[str] = None
    eway_bill_no: Optional[str] = None
    delivery_note: Optional[str] = None
    delivery_note_date: Optional[str] = None
    payment_mode_terms: Optional[str] = None
    reference_no: Optional[str] = None
    buyers_order_no: Optional[str] = None
    dispatch_doc_no: Optional[str] = None
    dispatched_through: Optional[str] = None
    destination: Optional[str] = None
    terms_of_delivery: Optional[str] = None
    other_references: Optional[str] = None
    order_date: Optional[str] = None
    items: List[InvoiceItem]
    total_taxable_value: float
    total_tax_amount: float
    grand_total: float

class ReceiptCreate(BaseModel):
    amount: float
    payment_date: str
    payment_method: str
    notes: Optional[str] = None

# --- Database Utilities ---

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Endpoints ---

@app.get("/api/profiles")
def get_profiles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, address_line_1, city, state_name, gstin, is_default, favicon_url FROM company_profile")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/profiles/{profile_id}")
def get_profile_by_id(profile_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_profile WHERE id=?", (profile_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    raise HTTPException(status_code=404, detail="Profile not found")

@app.get("/api/profile")
def get_profile():
    # Backward compatibility: return default or first profile
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_profile ORDER BY is_default DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

@app.post("/api/profiles")
def create_profile(profile: CompanyProfile):
    conn = get_db()
    cursor = conn.cursor()
    profile_id = str(uuid.uuid4())
    
    # Check if this is the first profile, make it default if so
    cursor.execute("SELECT COUNT(*) FROM company_profile")
    count = cursor.fetchone()[0]
    is_default = 1 if count == 0 else 0
    
    cursor.execute('''
        INSERT INTO company_profile (id, name, address_line_1, address_line_2, city, state_name, state_code, country, pincode, place_id, gstin, pan_number, bank_name, bank_branch, bank_account_no, bank_ifsc, bank_address, declaration_text, terms_conditions, email, mobile, landline, fax, is_default, favicon_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (profile_id, profile.name, profile.address_line_1, profile.address_line_2, profile.city, 
          profile.state_name, profile.state_code, profile.country, profile.pincode, profile.place_id, profile.gstin, profile.pan_number, 
          profile.bank_name, profile.bank_branch, profile.bank_account_no, profile.bank_ifsc, profile.bank_address, profile.declaration_text, profile.terms_conditions, profile.email, profile.mobile, profile.landline, profile.fax, is_default, profile.favicon_url))
    
    conn.commit()
    conn.close()
    return {"status": "success", "id": profile_id}

@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: str, profile: CompanyProfile):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM company_profile WHERE id=?", (profile_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    cursor.execute('''
        UPDATE company_profile SET name=?, address_line_1=?, address_line_2=?, city=?, state_name=?, 
        state_code=?, country=?, pincode=?, place_id=?, gstin=?, pan_number=?, bank_name=?, 
        bank_branch=?, bank_account_no=?, bank_ifsc=?, bank_address=?, declaration_text=?, 
        terms_conditions=?, email=?, mobile=?, landline=?, fax=?, favicon_url=? WHERE id=?
    ''', (profile.name, profile.address_line_1, profile.address_line_2, profile.city, 
          profile.state_name, profile.state_code, profile.country, profile.pincode, profile.place_id, 
          profile.gstin, profile.pan_number, profile.bank_name, profile.bank_branch, 
          profile.bank_account_no, profile.bank_ifsc, profile.bank_address, profile.declaration_text, 
          profile.terms_conditions, profile.email, profile.mobile, profile.landline, profile.fax, 
          profile.favicon_url, profile_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "id": profile_id}

@app.post("/api/profiles/{profile_id}/set-default")
def set_default_profile(profile_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM company_profile WHERE id=?", (profile_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    cursor.execute("UPDATE company_profile SET is_default = 0")
    cursor.execute("UPDATE company_profile SET is_default = 1 WHERE id=?", (profile_id,))
    
    conn.commit()
    conn.close()
    return {"status": "success", "id": profile_id}

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM company_profile WHERE id=?", (profile_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")

    cursor.execute("DELETE FROM company_profile WHERE id=?", (profile_id,))
    
    # If we deleted the default profile, set another one as default
    cursor.execute("SELECT COUNT(*) FROM company_profile WHERE is_default = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM company_profile LIMIT 1")
        first_row = cursor.fetchone()
        if first_row:
            cursor.execute("UPDATE company_profile SET is_default = 1 WHERE id=?", (first_row['id'],))

    conn.commit()
    conn.close()
    return {"status": "success", "id": profile_id}

@app.post("/api/profile")
def save_profile_legacy(profile: CompanyProfile):
    # Backward compatibility: update default or first profile
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM company_profile ORDER BY is_default DESC, created_at ASC LIMIT 1")
    existing = cursor.fetchone()
    
    if existing:
        return update_profile(existing['id'], profile)
    else:
        return create_profile(profile)

@app.get("/api/clients")
def get_clients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, billing_address_line_1, city, state_name, gstin FROM clients")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/clients/{client_id}")
def get_client_by_id(client_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    raise HTTPException(status_code=404, detail="Client not found")

@app.post("/api/clients")
def add_client(client: Client):
    conn = get_db()
    cursor = conn.cursor()
    client_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO clients (id, name, billing_address_line_1, billing_address_line_2, city, state_name, state_code, country, pincode, place_id, gstin, email, mobile, landline, fax)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, client.name, client.billing_address_line_1, client.billing_address_line_2,
          client.city, client.state_name, client.state_code, client.country, client.pincode,
          client.place_id, client.gstin, client.email, client.mobile, client.landline, client.fax))
    conn.commit()
    conn.close()
    return {"status": "success", "id": client_id}

@app.put("/api/clients/{client_id}")
def update_client(client_id: str, client: Client):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE id=?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    cursor.execute('''
        UPDATE clients SET name=?, billing_address_line_1=?, billing_address_line_2=?, city=?,
        state_name=?, state_code=?, country=?, pincode=?, place_id=?, gstin=?,
        email=?, mobile=?, landline=?, fax=? WHERE id=?
    ''', (client.name, client.billing_address_line_1, client.billing_address_line_2,
          client.city, client.state_name, client.state_code, client.country, client.pincode,
          client.place_id, client.gstin, client.email, client.mobile, client.landline, client.fax, client_id))
    conn.commit()
    conn.close()
    return {"status": "success", "id": client_id}

@app.delete("/api/clients/{client_id}")
def delete_client(client_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE id=?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    cursor.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "id": client_id}

@app.get("/api/shipping")
def get_all_shipping():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, c.name as client_name, s.branch_name, s.address_line_1, s.city, s.state_name, s.gstin, s.client_id
        FROM shipping_addresses s
        JOIN clients c ON s.client_id = c.id
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/clients/{client_id}/shipping")
def get_shipping(client_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shipping_addresses WHERE client_id = ?", (client_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/shipping/{ship_id}")
def get_shipping_by_id(ship_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shipping_addresses WHERE id=?", (ship_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    raise HTTPException(status_code=404, detail="Shipping address not found")

@app.post("/api/shipping")
def add_shipping(ship: ShippingAddress):
    conn = get_db()
    cursor = conn.cursor()
    ship_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO shipping_addresses (id, client_id, branch_name, address_line_1, address_line_2, city, state_name, state_code, country, pincode, place_id, gstin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ship_id, ship.client_id, ship.branch_name, ship.address_line_1, ship.address_line_2,
          ship.city, ship.state_name, ship.state_code, ship.country, ship.pincode, ship.place_id, ship.gstin))
    conn.commit()
    conn.close()
    return {"status": "success", "id": ship_id}

@app.put("/api/shipping/{ship_id}")
def update_shipping(ship_id: str, ship: ShippingAddress):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM shipping_addresses WHERE id=?", (ship_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Shipping address not found")
    cursor.execute('''
        UPDATE shipping_addresses SET client_id=?, branch_name=?, address_line_1=?, address_line_2=?,
        city=?, state_name=?, state_code=?, country=?, pincode=?, place_id=?, gstin=? WHERE id=?
    ''', (ship.client_id, ship.branch_name, ship.address_line_1, ship.address_line_2,
          ship.city, ship.state_name, ship.state_code, ship.country, ship.pincode, ship.place_id, ship.gstin, ship_id))
    conn.commit()
    conn.close()
    return {"status": "success", "id": ship_id}

@app.delete("/api/shipping/{ship_id}")
def delete_shipping(ship_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM shipping_addresses WHERE id=?", (ship_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Shipping address not found")
    cursor.execute("DELETE FROM shipping_addresses WHERE id=?", (ship_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "id": ship_id}

# ---- Items Master Endpoints ----

@app.get("/api/items")
def get_items():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items_master ORDER BY description ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/items/{item_id}")
def get_item_by_id(item_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items_master WHERE id=?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/api/items")
def add_item_master(item: ItemMaster):
    conn = get_db()
    cursor = conn.cursor()
    item_id = item.id or str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO items_master (id, description, hsn_sac, default_unit, gst_rate)
        VALUES (?, ?, ?, ?, ?)
    ''', (item_id, item.description, item.hsn_sac, item.default_unit, item.gst_rate))
    conn.commit()
    conn.close()
    return {"status": "success", "id": item_id}

@app.put("/api/items/{item_id}")
def update_item_master(item_id: str, item: ItemMaster):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM items_master WHERE id=?", (item_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute('''
        UPDATE items_master SET description=?, hsn_sac=?, default_unit=?, gst_rate=? WHERE id=?
    ''', (item.description, item.hsn_sac, item.default_unit, item.gst_rate, item_id))
    conn.commit()
    conn.close()
    return {"status": "success", "id": item_id}

@app.delete("/api/items/{item_id}")
def delete_item_master(item_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM items_master WHERE id=?", (item_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute("DELETE FROM items_master WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "id": item_id}

# ---- Invoice Endpoints ----

@app.get("/api/invoices/next-number")
def get_next_invoice_number():
    """Returns the next auto-generated invoice number based on count."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM invoices")
    count = cursor.fetchone()['cnt']
    conn.close()
    year = date.today().strftime("%Y-%m")
    return {"invoice_no": f"INV-{year}-{count+1:04d}"}

@app.get("/api/invoices")
def get_invoices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, i.invoice_no, i.invoice_date, i.grand_total, i.total_taxable_value, i.total_tax_amount,
               c.name as client_name
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        ORDER BY i.invoice_date DESC, i.created_at DESC
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/invoices/{inv_id}")
def get_invoice(inv_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id=?", (inv_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = dict(row)
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (inv_id,))
    inv['items'] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return inv

@app.get("/api/invoices/{inv_id}/pdf")
async def get_invoice_pdf(inv_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT invoice_no FROM invoices WHERE id = ?", (inv_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    safe_no = row['invoice_no'].replace('/', '_').replace(' ', '_')
    # Use an absolute tmp path next to the DB
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, f"Invoice_{safe_no}.pdf")
    html_path = os.path.join(base_dir, f"temp_{inv_id}.html")
    try:
        data = fetch_invoice_data(DB_PATH, inv_id)
        # Point Jinja2 loader at the Templates folder in project root
        template_dir = os.path.join(os.path.dirname(base_dir), 'Templates')
        renderer = InvoiceRenderer(template_dir=template_dir, template_file='gst_invoice.html')
        renderer.render(data, html_path)
        await generate_pdf(html_path, pdf_path)
        if os.path.exists(html_path):
            os.remove(html_path)
        return FileResponse(pdf_path, media_type='application/pdf',
                            filename=f"Invoice_{safe_no}.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/invoices")
async def create_invoice(inv: InvoiceCreate):
    conn = get_db()
    cursor = conn.cursor()
    # Use explicitly provided company_id or fall back to default
    company_id = getattr(inv, 'company_id', None)
    if not company_id:
        cursor.execute("SELECT id FROM company_profile WHERE is_default=1 LIMIT 1")
        comp = cursor.fetchone()
        if not comp:
            cursor.execute("SELECT id FROM company_profile LIMIT 1")
            comp = cursor.fetchone()
        if not comp:
            conn.close()
            raise HTTPException(status_code=400, detail="No company profile set up")
        company_id = comp['id']

    inv_id = str(uuid.uuid4())
    invoice_date = inv.invoice_date or date.today().isoformat()
    try:
        cursor.execute('''
            INSERT INTO invoices (
                id, company_id, client_id, shipping_id, invoice_no, invoice_date,
                eway_bill_no, delivery_note, delivery_note_date, payment_mode_terms,
                reference_no, buyers_order_no, dispatch_doc_no, dispatched_through,
                destination, terms_of_delivery,
                total_taxable_value, total_tax_amount, grand_total,
                other_references, order_date
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            inv_id, company_id, inv.client_id, inv.shipping_id or None,
            inv.invoice_no, invoice_date,
            inv.eway_bill_no, inv.delivery_note, inv.delivery_note_date,
            inv.payment_mode_terms, inv.reference_no, inv.buyers_order_no,
            inv.dispatch_doc_no, inv.dispatched_through, inv.destination,
            inv.terms_of_delivery,
            inv.total_taxable_value, inv.total_tax_amount, inv.grand_total,
            inv.other_references, inv.order_date
        ))
        for item in inv.items:
            # Auto-save item to Item Master if it doesn't exist (matched by description)
            cursor.execute("SELECT id FROM items_master WHERE description = ?", (item.description,))
            existing_item = cursor.fetchone()
            item_id = item.item_id
            
            if not existing_item:
                item_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO items_master (id, description, hsn_sac, default_unit, gst_rate)
                    VALUES (?, ?, ?, ?, ?)
                ''', (item_id, item.description, item.hsn_sac, item.unit, item.igst_rate))
            else:
                item_id = existing_item['id']

            cursor.execute('''
                INSERT INTO invoice_items (
                    id, invoice_id, item_id, description, hsn_sac, quantity, unit, rate,
                    taxable_value, cgst_rate, sgst_rate, igst_rate, tax_amount, total_amount
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                str(uuid.uuid4()), inv_id, item_id,
                item.description, item.hsn_sac, item.quantity, item.unit, item.rate,
                item.taxable_value, item.cgst_rate, item.sgst_rate, item.igst_rate,
                item.tax_amount, item.total_amount
            ))
        conn.commit()
        return {"status": "created", "invoice_id": inv_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/invoices/{inv_id}")
def delete_invoice(inv_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM invoices WHERE id=?", (inv_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
    cursor.execute("DELETE FROM invoice_items WHERE invoice_id=?", (inv_id,))
    cursor.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/api/invoices/{inv_id}/receipts")
def get_receipts(inv_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts WHERE invoice_id=? ORDER BY payment_date DESC, created_at DESC", (inv_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/invoices/{inv_id}/receipt")
def create_receipt(inv_id: str, receipt: ReceiptCreate):
    conn = get_db()
    cursor = conn.cursor()
    receipt_id = str(uuid.uuid4())
    try:
        cursor.execute('''
            INSERT INTO receipts (id, invoice_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (receipt_id, inv_id, receipt.amount, receipt.payment_date, receipt.payment_method, receipt.notes))
        conn.commit()
        return {"status": "success", "id": receipt_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/payments/report")
def get_payments_report(fy: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    # Updated query to show transaction-level detail
    query = '''
        SELECT 
            i.id as invoice_id, i.invoice_no, i.invoice_date, i.grand_total,
            c.name as client_name,
            r.amount as paid_amount, r.payment_date, r.payment_method,
            (SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE invoice_id = i.id) as total_paid_to_date
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        LEFT JOIN receipts r ON i.id = r.invoice_id
        WHERE 1=1
    '''
    # Execute and fetch all
    cursor.execute(query + " ORDER BY i.invoice_date DESC, r.payment_date DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # Filter by FY if requested
    if fy:
        rows = [r for r in rows if get_financial_year(r['invoice_date']) == fy]

    # Process rows for UI consistency
    for row in rows:
        grand_total = float(row.get('grand_total') or 0)
        total_paid = float(row.get('total_paid_to_date') or 0)
        row['amount_due'] = grand_total - total_paid
        
        if row['paid_amount'] is None:
            row['paid_amount'] = 0.0
            row['payment_date'] = "-"
            row['payment_method'] = "-"
        else:
            row['paid_amount'] = float(row['paid_amount'])
            
    return rows

@app.get("/api/payments/export")
def export_payments_excel(fy: Optional[str] = None):
    """Exports the payments report to an Excel file."""
    import pandas as pd
    data = get_payments_report(fy)
    if not data:
        # Return empty excel or skip
        df = pd.DataFrame(columns=["Sl No", "Invoice No", "Invoice Date", "Client Name", "Total Amount", "Amount Paid", "Amount Due"])
    else:
        # Prepare for DataFrame
        records = []
        for idx, r in enumerate(data):
            records.append({
                "Sl No": idx + 1,
                "Invoice No": r['invoice_no'],
                "Invoice Date": r['invoice_date'],
                "Client Name": r['client_name'],
                "Total Amount": r['grand_total'],
                "Paid Date": r['payment_date'],
                "Paid Mode": r['payment_method'],
                "Amount Paid": r['paid_amount'],
                "Balance Due": r['amount_due']
            })
        df = pd.DataFrame(records)
    
    # Write to buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Payments_Report')
    
    output.seek(0)
    
    fy_str = f"_{fy}" if fy else ""
    filename = f"Payments_Report{fy_str}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def get_financial_year(date_str: str) -> str:
    """Calculates Indian Financial Year (April 1 to March 31) from a YYYY-MM-DD string."""
    try:
        d = date.fromisoformat(date_str)
        year_val = d.year
        if d.month >= 4:
            next_year_suffix = f"{(year_val + 1) % 100:02d}"
            return f"{year_val}-{next_year_suffix}"
        else:
            prev_year_val = year_val - 1
            curr_year_suffix = f"{year_val % 100:02d}"
            return f"{prev_year_val}-{curr_year_suffix}"
    except (ValueError, TypeError):
        return "Unknown"

@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all invoices with their paid amounts
    cursor.execute('''
        SELECT 
            i.id, i.invoice_no, i.invoice_date, i.grand_total,
            COALESCE(SUM(r.amount), 0) as amount_paid
        FROM invoices i
        LEFT JOIN receipts r ON i.id = r.invoice_id
        GROUP BY i.id
    ''')
    invoices = cursor.fetchall()
    conn.close()

    # Aggregate by Financial Year
    summary_by_fy = {}
    
    for row in invoices:
        date_val = row['invoice_date']
        if not date_val: continue
        
        try:
            fy = get_financial_year(date_val)
        except:
            continue
        
        if fy not in summary_by_fy:
            summary_by_fy[fy] = {
                "financial_year": fy,
                "total_revenue": 0.0,
                "total_received": 0.0,
                "bills_receivable": 0.0,
                "invoice_count": 0
            }
            
        summary_by_fy[fy]["total_revenue"] = float(summary_by_fy[fy]["total_revenue"]) + float(row['grand_total'] or 0)
        summary_by_fy[fy]["total_received"] = float(summary_by_fy[fy]["total_received"]) + float(row['amount_paid'] or 0)
        summary_by_fy[fy]["bills_receivable"] = float(summary_by_fy[fy]["bills_receivable"]) + float((row['grand_total'] or 0) - (row['amount_paid'] or 0))
        summary_by_fy[fy]["invoice_count"] = int(summary_by_fy[fy]["invoice_count"]) + 1
        
        
    return list(summary_by_fy.values())

@app.get("/api/dashboard/charts")
def get_dashboard_charts(fy: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    # We need to filter by FY. 
    # For SQLite, it's easiest to fetch all relevant data and filter in Python,
    # or construct date blocks. Since get_financial_year is Python logic, we'll fetch all and filter.
    
    # 1. Top Clients
    cursor.execute('''
        SELECT 
            c.name as client_name, i.invoice_date, i.grand_total, i.id as invoice_id
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
    ''')
    all_invoices = cursor.fetchall()
    
    # 2. Top Products (by Name)
    cursor.execute('''
        SELECT 
            it.description as product_name, it.total_amount, i.invoice_date
        FROM invoice_items it
        JOIN invoices i ON it.invoice_id = i.id
    ''')
    all_items = cursor.fetchall()
    conn.close()
    
    # Filter by requested FY
    filtered_invoices = [inv for inv in all_invoices if get_financial_year(inv['invoice_date']) == fy]
    filtered_items = [itm for itm in all_items if get_financial_year(itm['invoice_date']) == fy]
    
    # Aggregate Monthly Trend
    monthly_trend = {f"{m:02d}": 0.0 for m in range(1, 13)}  # '01' to '12'
    client_totals = {}
    
    for inv in filtered_invoices:
        # Expected format YYYY-MM-DD
        date_str = inv['invoice_date']
        if date_str and len(date_str) >= 7:
            # Use split instead of slice to avoid linter confusion
            parts = date_str.split('-')
            if len(parts) >= 2:
                month = parts[1]
                if month in monthly_trend:
                    monthly_trend[month] = float(monthly_trend[month]) + float(inv['grand_total'] or 0)
        
        cname = inv['client_name'] or 'Unknown'
        client_totals[cname] = float(client_totals.get(cname, 0.0)) + float(inv['grand_total'] or 0.0)
        
    product_totals = {}
    for itm in filtered_items:
        pname = itm['product_name'] or 'Unknown'
        product_totals[pname] = float(product_totals.get(pname, 0.0)) + float(itm['total_amount'] or 0.0)
        
    # Sort Top Clients & Top Products
    sorted_clients = sorted([{"name": str(k), "value": float(v)} for k, v in client_totals.items()], key=lambda x: x['value'], reverse=True)
    top_clients = [sorted_clients[i] for i in range(min(10, len(sorted_clients)))]
    
    sorted_products = sorted([{"name": str(k), "value": float(v)} for k, v in product_totals.items()], key=lambda x: x['value'], reverse=True)
    top_products = [sorted_products[i] for i in range(min(10, len(sorted_products)))]
    
    # Remap months to Fiscal Year order (Apr..Mar)
    months_order = ['04', '05', '06', '07', '08', '09', '10', '11', '12', '01', '02', '03']
    month_names = {'01':'Jan', '02':'Feb', '03':'Mar', '04':'Apr', '05':'May', '06':'Jun', 
                   '07':'Jul', '08':'Aug', '09':'Sep', '10':'Oct', '11':'Nov', '12':'Dec'}
                   
    trend_labels = [month_names[m] for m in months_order]
    trend_data = [monthly_trend[m] for m in months_order]
    
    return {
        "monthly_trend": {"labels": trend_labels, "data": trend_data},
        "top_clients": {"labels": [c['name'] for c in top_clients], "data": [c['value'] for c in top_clients]},
        "top_products": {"labels": [p['name'] for p in top_products], "data": [p['value'] for p in top_products]}
    }


@app.get("/api/backup")
def download_backup():
    """Generates a zip backup of the SQLite database safely."""
    # Create an in-memory zip file containing the database
    backup_db_path = os.path.join(os.path.dirname(DB_PATH), "backup_temp.db")
    try:
        source = sqlite3.connect(DB_PATH)
        dest = sqlite3.connect(backup_db_path)
        with source, dest:
            source.backup(dest)
        dest.close()
        source.close()
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(backup_db_path, arcname="invoices.db")
        
        zip_buffer.seek(0)
        
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"GST_Invoice_Backup_{now_str}.zip"
        
        return StreamingResponse(
            zip_buffer, 
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(backup_db_path):
            try:
                os.remove(backup_db_path)
            except:
                pass

@app.post("/api/restore")
async def restore_backup(file: UploadFile = File(...)):
    """Restores the database from a zip backup."""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file containing invoices.db")
        
    content = await file.read()
    zip_buffer = io.BytesIO(content)
    
    try:
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            if "invoices.db" not in zip_ref.namelist():
                raise HTTPException(status_code=400, detail="ZIP file must contain invoices.db")
                
            # Safely create a fallback backup of current DB before replacing
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback_db_path = DB_PATH + f".fallback_{now_str}"
            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, fallback_db_path)
                
            # Extract and overwrite DB_PATH
            zip_ref.extract("invoices.db", path=os.path.dirname(DB_PATH))
            
            return {"status": "success", "message": "Database restored successfully"}
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP archive")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/profiles/{profile_id}/favicon")
async def upload_favicon(profile_id: str, file: UploadFile = File(...)):
    """Uploads a favicon for a profile."""
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.ico', '.png', '.jpg', '.jpeg', '.svg']:
        raise HTTPException(status_code=400, detail="Invalid file type. Use .ico, .png, .jpg, or .svg")

    filename = f"{profile_id}_favicon{ext}"
    file_path = os.path.join(FAVICONS_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update DB
    favicon_url = f"/uploads/favicons/{filename}"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE company_profile SET favicon_url=? WHERE id=?", (favicon_url, profile_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "favicon_url": favicon_url}
    
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT favicon_url FROM company_profile WHERE is_default=1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row and row['favicon_url']:
        # row['favicon_url'] example: "/uploads/favicons/uuid_favicon.png"
        rel_path = row['favicon_url'].replace('/uploads/', '')
        file_path = os.path.join(UPLOADS_DIR, rel_path.replace('/', os.sep))
        
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    # Fallback: check frontend/favicon.ico
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
    frontend_favicon = os.path.join(frontend_dir, "favicon.ico")
    if os.path.exists(frontend_favicon):
        return FileResponse(frontend_favicon)
        
    return Response(status_code=204) # No Content to stop 404 logs

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
