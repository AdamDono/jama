
import psycopg2
from app import get_db_connection

def migrate():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        print("Adding phone column to leads table...")
        cur.execute('ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone VARCHAR(50);')
        conn.commit()
        print("Migration successful: phone column added.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed or column already exists: {e}")

if __name__ == '__main__':
    migrate()
