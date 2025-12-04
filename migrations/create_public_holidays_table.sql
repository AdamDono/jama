CREATE TABLE IF NOT EXISTS public_holidays (
    id SERIAL PRIMARY KEY,
    holiday_date DATE NOT NULL UNIQUE,
    holiday_name VARCHAR(100) NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert South African Public Holidays for 2025
INSERT INTO public_holidays (holiday_date, holiday_name, is_recurring) VALUES
('2025-01-01', 'New Year''s Day', TRUE),
('2025-03-21', 'Human Rights Day', TRUE),
('2025-04-18', 'Good Friday', FALSE),
('2025-04-21', 'Family Day', FALSE),
('2025-04-27', 'Freedom Day', TRUE),
('2025-04-28', 'Freedom Day (Observed)', FALSE),
('2025-05-01', 'Workers'' Day', TRUE),
('2025-06-16', 'Youth Day', TRUE),
('2025-08-09', 'National Women''s Day', TRUE),
('2025-09-24', 'Heritage Day', TRUE),
('2025-12-16', 'Day of Reconciliation', TRUE),
('2025-12-25', 'Christmas Day', TRUE),
('2025-12-26', 'Day of Goodwill', TRUE)
ON CONFLICT (holiday_date) DO NOTHING;
