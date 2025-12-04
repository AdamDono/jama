import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def create_comments_table():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_comments (
                id SERIAL PRIMARY KEY,
                leave_application_id INTEGER REFERENCES leave_applications(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("✅ Leave comments table created successfully!")
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    create_comments_table()
