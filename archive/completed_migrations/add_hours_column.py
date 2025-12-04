import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def add_hours_column():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Add hours_worked column (for partial day leave)
        cur.execute("""
            ALTER TABLE leave_applications 
            ADD COLUMN IF NOT EXISTS hours_worked DECIMAL(3,1) DEFAULT NULL;
        """)
        print("Added hours_worked column")
        
        # Remove is_half_day column (no longer needed)
        cur.execute("""
            ALTER TABLE leave_applications 
            DROP COLUMN IF EXISTS is_half_day;
        """)
        print("Removed is_half_day column")
        
        conn.commit()
        print("✅ Hours-based leave support added successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    add_hours_column()
