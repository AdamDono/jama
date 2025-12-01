import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def clean_non_admin_users():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Get count before deletion
        cur.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
        count = cur.fetchone()[0]
        print(f"Found {count} non-admin users to delete")
        
        # Delete in correct order (foreign key constraints)
        cur.execute("""
            DELETE FROM leave_balance WHERE user_id IN (
                SELECT id FROM users WHERE role != 'admin'
            );
        """)
        print("Deleted leave balances")
        
        cur.execute("""
            DELETE FROM leave_applications WHERE user_id IN (
                SELECT id FROM users WHERE role != 'admin'
            );
        """)
        print("Deleted leave applications")
        
        cur.execute("""
            DELETE FROM employees WHERE user_id IN (
                SELECT id FROM users WHERE role != 'admin'
            );
        """)
        print("Deleted employees")
        
        cur.execute("DELETE FROM users WHERE role != 'admin';")
        print("Deleted non-admin users")
        
        conn.commit()
        print(f"\nSuccessfully cleaned {count} non-admin users and their data")
        
        # Show remaining users
        cur.execute("SELECT id, username, email, role FROM users")
        users = cur.fetchall()
        print(f"\nRemaining users ({len(users)}):")
        for user in users:
            print(f"  - {user[1]} ({user[2]}) - Role: {user[3]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    clean_non_admin_users()
