ALTER TABLE employees ADD COLUMN IF NOT EXISTS job_title VARCHAR(100);
UPDATE employees SET job_title = 'Employee' WHERE job_title IS NULL;
