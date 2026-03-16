import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoices.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('ALTER TABLE company_profile ADD COLUMN favicon_url TEXT')
        conn.commit()
        print("Successfully added favicon_url column.")
    except sqlite3.OperationalError:
        print("Column favicon_url already exists.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
