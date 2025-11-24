import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def check_user_role():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        cur.execute("SELECT id, username, email, role FROM users WHERE email = 'flipbrickzmusic1@gmail.com'")
        user = cur.fetchone()
        
        if user:
            print(f"User Found: ID={user[0]}, Username={user[1]}, Email={user[2]}, Role={user[3]}")
        else:
            print("User not found!")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user_role()
