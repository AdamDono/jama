import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def add_column():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("ALTER TABLE leave_balance ADD COLUMN IF NOT EXISTS unpaid_leave INTEGER DEFAULT 0;")
        conn.commit()
        print("Column 'unpaid_leave' added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
