import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def add_password_change_column():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Add must_change_password column
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
        """)
        
        conn.commit()
        print("Column 'must_change_password' added successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_password_change_column()
