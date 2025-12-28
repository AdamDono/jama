
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'jama'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', '5432')
    )
    cur = conn.cursor()
    
    tables = ['leave_applications', 'leave_balance']
    for table in tables:
        print(f"\n--- {table} ---")
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table}';
        """)
        for col in cur.fetchall():
            print(f"{col[0]}: {col[1]}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
