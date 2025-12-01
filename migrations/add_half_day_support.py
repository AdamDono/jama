import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def add_half_day_support():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Add is_half_day column
        cur.execute("""
            ALTER TABLE leave_applications 
            ADD COLUMN IF NOT EXISTS is_half_day BOOLEAN DEFAULT FALSE;
        """)
        print("Added is_half_day column")
        
        # Change days column to support decimals
        cur.execute("""
            ALTER TABLE leave_applications 
            ALTER COLUMN days TYPE DECIMAL(5,1);
        """)
        print("Changed days column to DECIMAL(5,1)")
        
        conn.commit()
        print("✅ Half-day leave support added successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    add_half_day_support()
