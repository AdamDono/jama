import psycopg2
import os

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433'
}

def run_migration():
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    
    try:
        with open('migrations/create_audit_logs_table.sql', 'r') as f:
            cur.execute(f.read())
        conn.commit()
        print("Migration successful: audit_logs table created.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
