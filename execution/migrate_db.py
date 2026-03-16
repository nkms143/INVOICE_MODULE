import sqlite3
import os

DB_PATH = r"c:\SUDA_WORKS\D\amar\AI PROJECTS\INVOICES\execution\invoices.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check company_profile
    cursor.execute("PRAGMA table_info(company_profile)")
    company_cols = [c[1] for c in cursor.fetchall()]
    
    company_missing = {
        'bank_branch': 'TEXT',
        'bank_address': 'TEXT',
        'email': 'TEXT',
        'mobile': 'TEXT',
        'landline': 'TEXT',
        'fax': 'TEXT',
        'is_default': 'INTEGER DEFAULT 0'
    }
    
    for col, type in company_missing.items():
        if col not in company_cols:
            print(f"Adding {col} to company_profile")
            try:
                cursor.execute(f"ALTER TABLE company_profile ADD COLUMN {col} {type}")
            except Exception as e:
                print(f"Error adding {col}: {e}")

    # 2. Check clients
    cursor.execute("PRAGMA table_info(clients)")
    client_cols = [c[1] for c in cursor.fetchall()]
    
    client_missing = {
        'billing_address_line_2': 'TEXT',
        'state_code': 'TEXT',
        'country': "TEXT DEFAULT 'India'",
        'pincode': 'TEXT',
        'place_id': 'TEXT',
        'email': 'TEXT',
        'mobile': 'TEXT',
        'landline': 'TEXT',
        'fax': 'TEXT'
    }
    
    for col, type in client_missing.items():
        if col not in client_cols:
            print(f"Adding {col} to clients")
            try:
                cursor.execute(f"ALTER TABLE clients ADD COLUMN {col} {type}")
            except Exception as e:
                print(f"Error adding {col}: {e}")
                
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
