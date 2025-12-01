-- Add last_annual_reset column to track when annual leave was last reset
-- This allows the system to automatically add 15 days each year on the employee's anniversary

ALTER TABLE leave_balance 
ADD COLUMN IF NOT EXISTS last_annual_reset DATE;

-- Set initial reset date to employee start date for existing employees
UPDATE leave_balance lb
SET last_annual_reset = e.start_date
FROM employees e
WHERE lb.user_id = e.user_id
AND lb.last_annual_reset IS NULL;

COMMENT ON COLUMN leave_balance.last_annual_reset IS 'Date when annual leave was last reset/renewed (typically on employment anniversary)';
