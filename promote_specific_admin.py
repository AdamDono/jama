import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def promote_specific_admin():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Check if user exists first
        cur.execute("SELECT id FROM users WHERE email = 'flipbrickzmusic1@gmail.com'")
        user = cur.fetchone()
        
        if user:
            cur.execute("UPDATE users SET role = 'admin' WHERE email = 'flipbrickzmusic1@gmail.com'")
            conn.commit()
            print("User 'flipbrickzmusic1@gmail.com' promoted to admin role.")
        else:
            print("User not found!")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    promote_specific_admin()
