import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def add_days_column():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("ALTER TABLE leave_applications ADD COLUMN IF NOT EXISTS days INTEGER;")
        conn.commit()
        print("Column 'days' added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_days_column()
