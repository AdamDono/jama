import psycopg2

DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
    'port': '5433',  
}

def change_leave_balance_to_decimal():
    try:
        conn = psycopg2.connect(**DATABASE)
        cur = conn.cursor()
        
        # Change all leave columns to DECIMAL to support partial days
        cur.execute("""
            ALTER TABLE leave_balance 
            ALTER COLUMN annual_leave TYPE DECIMAL(6,2);
        """)
        print("Changed annual_leave to DECIMAL(6,2)")
        
        cur.execute("""
            ALTER TABLE leave_balance 
            ALTER COLUMN sick_leave TYPE DECIMAL(6,2);
        """)
        print("Changed sick_leave to DECIMAL(6,2)")
        
        cur.execute("""
            ALTER TABLE leave_balance 
            ALTER COLUMN family_leave TYPE DECIMAL(6,2);
        """)
        print("Changed family_leave to DECIMAL(6,2)")
        
        cur.execute("""
            ALTER TABLE leave_balance 
            ALTER COLUMN unpaid_leave TYPE DECIMAL(6,2);
        """)
        print("Changed unpaid_leave to DECIMAL(6,2)")
        
        conn.commit()
        print("✅ Leave balance columns now support decimal values!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    change_leave_balance_to_decimal()
