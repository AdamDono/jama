#!/usr/bin/env python3
"""
Add last_annual_reset column to leave_balance table.
This enables automatic annual leave renewal on employee anniversaries.
"""

import psycopg2
from psycopg2.extras import DictCursor

# Database connection
conn = psycopg2.connect(
    dbname="leave_management",
    user="dam1mac89",
    password="",
    host="localhost"
)

cur = conn.cursor(cursor_factory=DictCursor)

try:
    print("Adding last_annual_reset column to leave_balance table...")
    
    # Add the column
    cur.execute('''
        ALTER TABLE leave_balance 
        ADD COLUMN IF NOT EXISTS last_annual_reset DATE
    ''')
    
    # Set initial reset date to employee start date for existing employees
    cur.execute('''
        UPDATE leave_balance lb
        SET last_annual_reset = e.start_date
        FROM employees e
        WHERE lb.user_id = e.user_id
        AND lb.last_annual_reset IS NULL
    ''')
    
    rows_updated = cur.rowcount
    conn.commit()
    
    print(f"✅ Successfully added last_annual_reset column")
    print(f"✅ Updated {rows_updated} existing employee records")
    print("\n🎉 Annual leave reset system is now active!")
    print("\nHow it works:")
    print("  - Leave accrues daily at 0.0411 days/day (15 days/year)")
    print("  - Every 365 days from last reset, employees get 15 more days")
    print("  - Maximum balance: 30 days (allows 15-day carry-over)")
    print("  - System checks automatically when users log in")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cur.close()
    conn.close()
