import psycopg2
from psycopg2.extras import DictCursor

conn = psycopg2.connect(
    dbname="jama",
    user="postgres",
    password="Fliph106",
    host="localhost",
    port="5433"
)

cur = conn.cursor(cursor_factory=DictCursor)

try:
    print("Adding job_title column to employees table...")
    
    with open('migrations/add_job_title.sql', 'r') as f:
        cur.execute(f.read())
    
    conn.commit()
    print("✅ Successfully added job_title column")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cur.close()
    conn.close()
