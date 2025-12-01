import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def check_leave_balance_schema():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'leave_balance'
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print("leave_balance table schema:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} (default: {col[2]})")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_leave_balance_schema()
