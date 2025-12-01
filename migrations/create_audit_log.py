import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def create_audit_log_table():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                action_type VARCHAR(50) NOT NULL,
                performed_by INTEGER REFERENCES users(id),
                target_id INTEGER,
                target_type VARCHAR(50),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("✅ Audit log table created successfully!")
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    create_audit_log_table()
