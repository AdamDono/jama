import psycopg2
from psycopg2.extras import DictCursor

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def check_schema():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Check leave_applications columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'leave_applications';
        """)
        columns = cur.fetchall()
        print("Columns in leave_applications:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
