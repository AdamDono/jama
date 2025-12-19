
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'jama'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', '5432')
    )

def apply_migration():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='leave_balance' AND column_name='updated_at';
        """)
        
        if not cur.fetchone():
            print("Adding updated_at column to leave_balance table...")
            cur.execute("""
                ALTER TABLE leave_balance 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            
            # Initialize with current time for existing records
            cur.execute("UPDATE leave_balance SET updated_at = CURRENT_TIMESTAMP;")
            
            conn.commit()
            print("Migration successful: updated_at column added.")
        else:
            print("Column updated_at already exists.")
            
    except Exception as e:
        conn.rollback()
        print(f"Error applying migration: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    apply_migration()
