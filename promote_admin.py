import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def promote_admin():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
        conn.commit()
        print("User 'admin' promoted to admin role.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    promote_admin()
