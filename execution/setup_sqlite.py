import sqlite3
import uuid
import os

def setup_database(db_path="invoices.db"):
    # Delete existing database for a clean start during development
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Initializing SQLite database at: {os.path.abspath(db_path)}")

    # 1. company_profile (Our Business)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_profile (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address_line_1 TEXT,
            address_line_2 TEXT,
            city TEXT,
            state_name TEXT,
            state_code TEXT NOT NULL,
            country TEXT DEFAULT 'India',
            pincode TEXT,
            place_id TEXT,
            gstin TEXT,
            pan_number TEXT,
            bank_name TEXT,
            bank_account_no TEXT,
            bank_ifsc TEXT,
            declaration_text TEXT,
            terms_conditions TEXT,
            favicon_url TEXT
        )
    ''')

    # 2. clients (The Buyers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            billing_address_line_1 TEXT,
            billing_address_line_2 TEXT,
            city TEXT,
            state_name TEXT,
            state_code TEXT NOT NULL,
            country TEXT DEFAULT 'India',
            pincode TEXT,
            place_id TEXT,
            gstin TEXT
        )
    ''')

    # 3. shipping_addresses (Consignee Branches)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipping_addresses (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            branch_name TEXT,
            address_line_1 TEXT,
            address_line_2 TEXT,
            city TEXT,
            state_name TEXT,
            state_code TEXT NOT NULL,
            country TEXT DEFAULT 'India',
            pincode TEXT,
            place_id TEXT,
            gstin TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')

    # 4. items_master (Product/Service Catalog)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items_master (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            hsn_sac TEXT,
            default_unit TEXT,
            gst_rate REAL DEFAULT 18.00
        )
    ''')

    # 5. invoices
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            shipping_id TEXT,
            invoice_no TEXT UNIQUE NOT NULL,
            invoice_date DATE DEFAULT CURRENT_DATE,
            eway_bill_no TEXT,
            delivery_note TEXT,
            delivery_note_date DATE,
            payment_mode_terms TEXT,
            reference_no TEXT,
            buyers_order_no TEXT,
            dispatch_doc_no TEXT,
            dispatched_through TEXT,
            destination TEXT,
            terms_of_delivery TEXT,
            total_taxable_value REAL,
            total_tax_amount REAL,
            grand_total REAL,
            FOREIGN KEY (company_id) REFERENCES company_profile (id),
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (shipping_id) REFERENCES shipping_addresses (id)
        )
    ''')

    # 6. invoice_items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            item_id TEXT,
            description TEXT NOT NULL,
            hsn_sac TEXT,
            quantity REAL,
            unit TEXT,
            rate REAL,
            taxable_value REAL,
            cgst_rate REAL DEFAULT 0,
            sgst_rate REAL DEFAULT 0,
            igst_rate REAL DEFAULT 0,
            tax_amount REAL,
            total_amount REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (item_id) REFERENCES items_master (id)
        )
    ''')

    # 7. receipts (Payment Tracking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            payment_method TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')

    print("Tables created successfully.")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
