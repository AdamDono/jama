#!/usr/bin/env python3
"""
Fix leave balances to correct default values.
Run this script to update existing employee leave balances.
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
    # Update all leave balances to correct defaults
    # Annual leave: 0 (will accrue at 1.7 days/month, max 15/year)
    # Sick leave: 30 days/year
    # Family leave: 3 days/year
    
    print("Updating leave balances to correct defaults...")
    
    cur.execute('''
        UPDATE leave_balance 
        SET annual_leave = 0,
            sick_leave = 30,
            family_leave = 3
    ''')
    
    rows_updated = cur.rowcount
    conn.commit()
    
    print(f"✅ Successfully updated {rows_updated} leave balance records")
    print("\nNew defaults:")
    print("  - Annual Leave: 0 days (accrues at 1.7 days/month, max 15/year)")
    print("  - Sick Leave: 30 days/year")
    print("  - Family Responsibility Leave: 3 days/year")
    print("\nNote: Annual leave will show accrued days based on employee start date.")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error updating leave balances: {e}")
finally:
    cur.close()
    conn.close()
