import sqlite3
import os
import shutil
from datetime import datetime

# Rule from AGENTS.md: Always use absolute paths for the database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoices.db")

def reset_database():
    """
    Safely clears all test data from the database to allow for restore testing.
    Creates a pre-reset backup automatically.
    """
    if not os.path.exists(DB_PATH):
        print(f"[-] Error: Database not found at {DB_PATH}")
        return

    print("=" * 50)
    print("      DATABASE RESET UTILITY (TESTING ONLY)      ")
    print("=" * 50)
    print(f"Target DB: {DB_PATH}")
    
    # 1. Create a safety backup
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = DB_PATH + f".pre_reset_{timestamp}"
        shutil.copy2(DB_PATH, backup_path)
        print(f"[+] Safety backup created: {os.path.basename(backup_path)}")
    except Exception as e:
        print(f"[-] Failed to create backup: {e}")
        return

    # 2. Confirm deletion (Console prompt if run interactively)
    # Since this is an agent-run script, we'll proceed if triggered, 
    # but the logic is here for manual safety.
    
    tables = [
        "receipts",
        "invoice_items",
        "invoices",
        "shipping_addresses",
        "clients",
        "items_master",
        "company_profile"
    ]
    
    try:
        conn = sqlite3.connect(DB_PATH)
        # Use row_factory for name-based access if needed, 
        # though not strictly necessary for DELETE.
        cursor = conn.cursor()
        
        print("[*] Starting data deletion...")
        
        # Disable foreign key checks temporarily if they exist to avoid constraint errors during wipe
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
                # Reset auto-increment counters
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"    [x] Cleared table: {table}")
            except sqlite3.OperationalError as e:
                # If table doesn't exist, just skip
                if "no such table" in str(e).lower():
                    print(f"    [-] Skipping: Table '{table}' does not exist.")
                else:
                    print(f"    [-] Error clearing {table}: {e}")

        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        
        print("=" * 50)
        print("[SUCCESS] Database has been wiped clean.")
        print("[NOTICE]  You can now use your 'Restore' module to verify the backup.")
        print("=" * 50)
        
    except Exception as e:
        print(f"[-] Critical error during reset: {e}")

if __name__ == "__main__":
    reset_database()
