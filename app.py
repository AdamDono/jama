from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from werkzeug.utils import secure_filename  # <-- Add this
from psycopg2.extras import DictCursor 
import psycopg2.extras  # Add this line
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_annual_leave(start_date):
    """
    Calculate annual leave accrual based on start date with annual reset.
    - Accrues at 1.25 days per month (15 days per year)
    - Daily accrual: 15 days ÷ 365 days = 0.0411 days per day
    - Resets annually on anniversary date
    - Allows carry-over up to 30 days maximum
    
    Returns: Accrued leave for CURRENT YEAR ONLY (not total balance)
    """
    from datetime import datetime
    
    if not start_date:
        return 0.0
    
    # Convert to date object if string
    now = datetime.now().date()
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # Calculate total days elapsed
    days_elapsed = (now - start_date).days
    
    # If negative (future date), return 0
    if days_elapsed < 0:
        return 0.0
    
    # Calculate which year of employment we're in
    years_completed = days_elapsed // 365
    days_in_current_year = days_elapsed % 365
    
    # Calculate accrued leave for current year only
    daily_accrual_rate = 15.0 / 365.0  # 0.0411 days per day
    current_year_accrual = days_in_current_year * daily_accrual_rate
    
    # Cap current year accrual at 15 days
    current_year_accrual = min(current_year_accrual, 15.0)
    
    return float(round(current_year_accrual, 2))

def check_and_reset_annual_leave(user_id, start_date, current_balance):
    """
    Check if employee has passed their anniversary and needs annual leave reset.
    Returns the updated balance after any necessary reset.
    """
    from datetime import datetime
    
    if not start_date:
        return current_balance
    
    now = datetime.now().date()
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # Calculate the most recent anniversary
    years_since_start = (now - start_date).days // 365
    
    if years_since_start < 1:
        # Less than 1 year employed, no reset needed
        return current_balance
    
    # Calculate the last anniversary date
    last_anniversary = start_date.replace(year=start_date.year + years_since_start)
    
    # Check if we've passed an anniversary that hasn't been processed
    # We'll use a simple check: if current balance + accrued is less than expected
    # This is a simplified approach - in production you'd track last_reset_date
    
    return current_balance

def log_action(action_type, performed_by, target_id=None, target_type=None, details=None):
    """
    Log an action to the audit trail.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO audit_log (action_type, performed_by, target_id, target_type, details)
            VALUES (%s, %s, %s, %s, %s)
        ''', (action_type, performed_by, target_id, target_type, details))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")



def get_db_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'jama'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', '5432')
    )

def log_audit(admin_id, action, target_type, target_id, details=None):
    """Helper function to log admin actions"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO audit_logs (admin_id, action, target_type, target_id, details)
            VALUES (%s, %s, %s, %s, %s)
        ''', (admin_id, action, target_type, target_id, details))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to log audit: {e}")


conn = get_db_connection()
cur = conn.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
cur.close()
conn.close()

with app.app_context():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            full_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) UNIQUE NOT NULL,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            start_date DATE NOT NULL,
            department VARCHAR(50) NOT NULL,
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    
# Signup route removed - employees are created by admin only
# Users get accounts automatically when admin creates an employee
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 
        
        try:
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            
            if user and check_password_hash(user['password'], password):
            
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_role'] = user['role']
                
                # Check if password change is required
                if user.get('must_change_password', False):
                    flash('Please change your password', 'warning')
                    return redirect(url_for('change_password'))
                
                flash('Login successful!', 'success')
                return redirect(url_for('landing'))
            else:
                flash('Invalid credentials!', 'error')
                return redirect(url_for('login'))
                
        finally:
            cur.close()
            conn.close()
            
    return render_template('login.html')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate passwords match
        if new_password != confirm_password:
            flash('New passwords do not match!', 'error')
            return redirect(url_for('change_password'))
        
        # Validate minimum length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return redirect(url_for('change_password'))
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        try:
            # Verify current password
            cur.execute('SELECT password FROM users WHERE id = %s', (session['user_id'],))
            user = cur.fetchone()
            
            if not user or not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect!', 'error')
                return redirect(url_for('change_password'))
            
            # Update password
            hashed_new_password = generate_password_hash(new_password)
            cur.execute('''
                UPDATE users 
                SET password = %s, must_change_password = FALSE 
                WHERE id = %s
            ''', (hashed_new_password, session['user_id']))
            
            conn.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('landing'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error changing password: {str(e)}', 'error')
            return redirect(url_for('change_password'))
        finally:
            cur.close()
            conn.close()
    
    return render_template('change_password.html')

# Add Employee Route
# ---------------------------
# ADD EMPLOYEE ROUTES (NEW)
# ---------------------------

# Show Form (GET)
@app.route('/add_employee_form', methods=['GET'])
def show_add_form():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('add_employee.html')

# Handle Submission (POST)
@app.route('/add_employee', methods=['POST'])
def handle_submission():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        full_name = request.form['full_name']
        phone = request.form['phone']
        employee_id = request.form['employee_id']
        start_date = request.form['start_date']
        department = request.form['department']
        role = request.form.get('role', 'employee')  # Get role selection
        profile_picture = None

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        # Check if employee_id or phone already exists
        cur.execute('SELECT * FROM employees WHERE phone=%s OR employee_id=%s', (phone, employee_id))
        if cur.fetchone():
            flash('Phone/ID already exists!', 'error')
            return redirect(url_for('show_add_form'))
        
        # Check if employee ID already exists
        cur.execute('SELECT id FROM employees WHERE employee_id = %s', (employee_id,))
        if cur.fetchone():
            flash('Employee ID already exists!', 'error')
            return redirect(url_for('show_add_form'))

        # Check if username (full_name) already exists
        cur.execute('SELECT * FROM users WHERE username=%s', (full_name,))
        if cur.fetchone():
            flash('An employee with this name already exists!', 'error')
            return redirect(url_for('show_add_form'))

        # Create user account first
        hashed_password = generate_password_hash(employee_id)  # Password = employee_id
        cur.execute('''
            INSERT INTO users (username, email, password, role, must_change_password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (full_name, f"{employee_id}@company.com", hashed_password, role, True))
        
        new_user_id = cur.fetchone()['id']

        # Create employee record
        cur.execute('''
            INSERT INTO employees 
            (user_id, full_name, phone, employee_id, start_date, department, job_title, profile_picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (new_user_id, full_name, phone, employee_id, start_date, department, job_title, profile_picture))
        
        # Create leave balance (0 annual, 30 sick, 3 family)
        cur.execute('''
            INSERT INTO leave_balance (user_id, annual_leave, sick_leave, family_leave, unpaid_leave)
            VALUES (%s, %s, %s, %s, %s)
        ''', (new_user_id, 0, 30, 3, 0))
        
        conn.commit()
        
        # Log audit
        log_audit(session['user_id'], 'Add Employee', 'Employee', new_user_id, 
                 f"Added employee {full_name} ({employee_id}) as {role}")

        flash(f'Employee added! Login: {full_name} / Password: {employee_id} (must change on first login)', 'success')
        return redirect(url_for('landing'))

    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('show_add_form'))
    
    finally:
        cur.close()
        conn.close()

@app.route('/admin/leaves')
def admin_leaves():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    department_filter = request.args.get('department', 'all')
    
    # Build query with filters
    query = '''
        SELECT l.*, e.full_name, e.department,
               COALESCE(COUNT(c.id), 0) as comment_count
        FROM leave_applications l
        JOIN employees e ON l.user_id = e.user_id
        LEFT JOIN leave_comments c ON l.id = c.leave_application_id
        WHERE 1=1
    '''
    params = []
    
    if status_filter != 'all':
        query += ' AND LOWER(l.status) = LOWER(%s)'
        params.append(status_filter)
    
    if department_filter != 'all':
        query += ' AND e.department = %s'
        params.append(department_filter)
    
    query += ' GROUP BY l.id, e.full_name, e.department ORDER BY l.created_at DESC'
    
    cur.execute(query, params)
    pending_leaves = cur.fetchall()
    
    # Get unique departments for filter dropdown
    cur.execute('SELECT DISTINCT department FROM employees WHERE department IS NOT NULL ORDER BY department')
    departments = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin_leaves.html', 
                         pending_leaves=pending_leaves,
                         departments=departments,
                         status_filter=status_filter,
                         department_filter=department_filter)
    
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    # Check if user has an employee record
    cur.execute('SELECT * FROM employees WHERE user_id = %s', (session['user_id'],))
    employee_check = cur.fetchone()
    
    if not employee_check:
        # If user is admin, create a default employee record
        if session.get('user_role') == 'admin':
            try:
                # Generate employee_id
                cur.execute('SELECT MAX(id) FROM employees')
                max_id = cur.fetchone()[0]
                employee_id = f"EMP{(max_id or 0) + 1:04d}"
                
                cur.execute('''
                    INSERT INTO employees (user_id, employee_id, full_name, phone, department, start_date, profile_picture)
                    VALUES (%s, %s, %s, %s, 'Management', CURRENT_DATE, NULL)
                ''', (session['user_id'], employee_id, session.get('username', 'Admin'), ''))
                
                # Initialize leave balance with correct defaults
                # Annual: 0 (accrues at 1.7 days/month, max 15/year)
                # Sick: 30 days/year
                # Family: 3 days/year
                cur.execute('''
                    INSERT INTO leave_balance (user_id, annual_leave, sick_leave, family_leave, last_annual_reset)
                    VALUES (%s, 0, 30, 3, CURRENT_DATE)
                ''', (session['user_id'],))
                
                conn.commit()
                flash('Default admin profile created.', 'success')
                
                # Re-fetch the new employee record
                cur.execute('SELECT * FROM employees WHERE user_id = %s', (session['user_id'],))
                employee_check = cur.fetchone()
            except Exception as e:
                conn.rollback()
                flash(f'Error creating profile: {str(e)}', 'error')
                return redirect(url_for('landing'))
        else:
            flash('Profile not available. Please contact administrator.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('landing'))
    
    try:
        if request.method == 'POST':
            # Handle profile update
            full_name = request.form['full_name']
            phone = request.form['phone']
            department = request.form.get('department') # Department might be disabled in form
            
            # If department is not in form (disabled), keep existing
            if not department:
                cur.execute('SELECT department FROM employees WHERE user_id = %s', (session['user_id'],))
                department = cur.fetchone()[0]

            job_title = request.form.get('job_title')
            if not job_title:
                 cur.execute('SELECT job_title FROM employees WHERE user_id = %s', (session['user_id'],))
                 result = cur.fetchone()
                 job_title = result[0] if result else None

            profile_picture = None
            
            # Get current employee data
            cur.execute('SELECT * FROM employees WHERE user_id = %s', (session['user_id'],))
            current_employee = cur.fetchone()
            
            if not current_employee:
                flash('Employee record not found!', 'error')
                return redirect(url_for('landing'))
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    profile_picture = filename
                else:
                    profile_picture = current_employee['profile_picture']
            else:
                profile_picture = current_employee['profile_picture']
            
            # Update employee record
            cur.execute('''
                UPDATE employees 
                SET full_name = %s, phone = %s, department = %s, job_title = %s, profile_picture = %s
                WHERE user_id = %s
            ''', (full_name, phone, department, job_title, profile_picture, session['user_id']))
            
            # Update username in users table
            cur.execute('''
                UPDATE users 
                SET username = %s
                WHERE id = %s
            ''', (full_name, session['user_id']))
            
            # Update session username
            session['username'] = full_name
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        
        # GET request - display profile
        cur.execute('SELECT * FROM employees WHERE user_id = %s', (session['user_id'],))
        employee = cur.fetchone()
        
        cur.execute('SELECT * FROM leave_balance WHERE user_id = %s', (session['user_id'],))
        leave_balance = cur.fetchone()
        
        calculated_annual_leave = 0
        if employee and employee['start_date']:
            # Calculate accrued annual leave using daily accrual
            start_date = employee['start_date']
            days_elapsed = (datetime.now().date() - start_date).days
            daily_accrual_rate = 15.0 / 365.0  # 0.0411 days per day
            accrued_leave = days_elapsed * daily_accrual_rate
            calculated_annual_leave = min(round(float(accrued_leave), 2), 15.0)
        else:
            calculated_annual_leave = 0
        
        return render_template('profile.html', 
                             employee=employee,
                             leave_balance=leave_balance,
                             calculated_annual_leave=calculated_annual_leave)
    
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('landing'))
    finally:
        cur.close()
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



def get_public_holidays():
    """Fetch all public holidays from database and expand recurring ones"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute('SELECT * FROM public_holidays')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    holidays = {}
    current_year = datetime.now().year
    # Generate for 10 years back and 10 years forward
    years_range = range(current_year - 5, current_year + 11)

    for row in rows:
        date_obj = row['holiday_date']
        name = row['holiday_name']
        is_recurring = row['is_recurring']

        if is_recurring:
            # Generate for all years in range
            for year in years_range:
                try:
                    # Handle leap years etc by using the same month/day
                    new_date = date_obj.replace(year=year)
                    holidays[new_date.strftime('%Y-%m-%d')] = name
                except ValueError:
                    # Handle Feb 29 on non-leap years if applicable
                    continue
        else:
            # Add the specific non-recurring date
            holidays[date_obj.strftime('%Y-%m-%d')] = name
            
    # Apply Sunday Rule: If a public holiday falls on a Sunday, the following Monday is a public holiday
    observed_holidays = {}
    for date_str, name in holidays.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj.weekday() == 6:  # Sunday
            monday_date = date_obj + timedelta(days=1)
            monday_str = monday_date.strftime('%Y-%m-%d')
            
            # Only add if Monday is not already a holiday
            if monday_str not in holidays:
                observed_holidays[monday_str] = f"{name} (Observed)"
    
    holidays.update(observed_holidays)
            
    return holidays

@app.route('/employee_dashboard')
def employee_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'user_id' not in session or session.get('user_role') != 'employee':
        return redirect(url_for('landing'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    # Fetch user's leave balance
    cur.execute('SELECT * FROM leave_balance WHERE user_id = %s', (session['user_id'],))
    leave_balance = cur.fetchone()
    
    # Get employee details for annual leave calculation
    cur.execute('SELECT * FROM employees WHERE user_id = %s', (session['user_id'],))
    employee = cur.fetchone()
    
    # Calculate annual leave
    if employee and employee.get('start_date'):
        accrued_annual_leave = calculate_annual_leave(employee['start_date'])
        stored_balance = float(leave_balance['annual_leave']) if leave_balance else 0.0
        calculated_annual_leave = float(accrued_annual_leave) + stored_balance
    else:
        calculated_annual_leave = 0
    
    # Fetch user's leave applications to show on calendar
    cur.execute('''
        SELECT * FROM leave_applications 
        WHERE user_id = %s 
        AND status != 'Rejected'
    ''', (session['user_id'],))
    leave_apps = cur.fetchall()
    
    # Process leave applications into a dictionary keyed by date
    leave_dates = {}
    for app in leave_apps:
        start = app['start_date']
        end = app['end_date']
        delta = (end - start).days + 1
        for i in range(delta):
            day = start + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            if date_str not in leave_dates:
                leave_dates[date_str] = []
            leave_dates[date_str].append({
                'type': app['leave_type'],
                'status': app['status']
            })

    # Get public holidays
    public_holidays = get_public_holidays()
    
    # Fetch all leave history for this employee (all statuses)
    cur.execute('''
        SELECT * FROM leave_applications 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    leave_history = cur.fetchall()
    
    # Calendar logic
    year = datetime.now().year
    month = datetime.now().month
    
    # Handle month navigation
    if request.args.get('year') and request.args.get('month'):
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    calendar_data = {
        'year': year,
        'month': month,
        'month_name': month_name,
        'calendar': cal,
        'current_day': datetime.now().day,
        'current_month': datetime.now().month,
        'current_year': datetime.now().year
    }
    
    cur.close()
    conn.close()
    
    return render_template('employee_dashboard.html', 
                         leave_balance=leave_balance,
                         calculated_annual_leave=calculated_annual_leave,
                         calendar_data=calendar_data,
                         leave_dates=leave_dates,
                         public_holidays=public_holidays,
                         leave_history=leave_history)

@app.route('/landing')
def landing():

    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Redirect employees to their dashboard
    if session.get('user_role') != 'admin':
        return redirect(url_for('employee_dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Initialize variables
    employees = []
    leaves = []
    leave_balance = None
    calculated_annual_leave = 0
    user_role = session.get('user_role', 'employee')
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 employees per page
    
    try:
        # Fetch the user's role (if not already in session or for safety)
        if 'user_role' not in session:
            cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
            db_user_role = cur.fetchone()
            if db_user_role:
                user_role = db_user_role['role']
                session['user_role'] = user_role # Store in session for future requests
            else:
                # Handle case where user role is not found (shouldn't happen if user_id is valid)
                flash('User role not found.', 'error')
                return redirect(url_for('login'))

        if user_role == 'admin':
            # Fetch total count for pagination
            cur.execute('SELECT COUNT(*) FROM employees')
            total_employees = cur.fetchone()[0]
            total_pages = (total_employees + per_page - 1) // per_page  # Ceiling division
            
            # Fetch paginated employees
            offset = (page - 1) * per_page
            cur.execute('''
                SELECT * FROM employees 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            ''', (per_page, offset))
            employees = cur.fetchall()
        else:
            total_pages = 1  # No pagination for non-admin
            cur.execute('SELECT * FROM employees WHERE user_id = %s ORDER BY created_at DESC', (session['user_id'],))
            employees = cur.fetchall()

            # Fetch the user's leave applications with comment counts
            cur.execute('''
                SELECT l.*, 
                       COALESCE(COUNT(c.id), 0) as comment_count
                FROM leave_applications l
                LEFT JOIN leave_comments c ON l.id = c.leave_application_id
                WHERE l.user_id = %s 
                GROUP BY l.id
                ORDER BY l.created_at DESC
            ''', (session['user_id'],))
            leaves = cur.fetchall()

        # Fetch the user's leave balance
        cur.execute('SELECT * FROM leave_balance WHERE user_id = %s', (session['user_id'],))
        leave_balance = cur.fetchone()
        
        # Get employee start date to calculate annual leave
        cur.execute('SELECT start_date FROM employees WHERE user_id = %s', (session['user_id'],))
        employee = cur.fetchone()
        
        # Check if annual leave needs to be reset (anniversary passed)
        if employee and employee['start_date'] and leave_balance:
            start_date = employee['start_date']
            now = datetime.now().date()
            
            # Get last reset date (or use start date if never reset)
            last_reset = leave_balance.get('last_annual_reset') or start_date
            
            # Calculate next anniversary after last reset
            years_since_last_reset = (now - last_reset).days // 365
            
            if years_since_last_reset >= 1:
                # Anniversary has passed! Add 15 days to annual leave
                current_annual = float(leave_balance['annual_leave'])
                new_annual = min(current_annual + 15.0, 30.0)  # Cap at 30 days (15 carry-over)
                
                # Update the balance and reset date
                cur.execute('''
                    UPDATE leave_balance 
                    SET annual_leave = %s,
                        last_annual_reset = %s
                    WHERE user_id = %s
                ''', (new_annual, now, session['user_id']))
                conn.commit()
                
                # Re-fetch updated balance
                cur.execute('SELECT * FROM leave_balance WHERE user_id = %s', (session['user_id'],))
                leave_balance = cur.fetchone()
                
                flash(f'🎉 Annual leave renewed! You received 15 days. New balance: {new_annual} days', 'success')
        
        if employee and employee['start_date']:
            # Calculate accrued leave based on start date
            accrued_annual_leave = calculate_annual_leave(employee['start_date'])
            # Add the stored balance (which tracks deductions and can be negative)
            # Net = Accrued + Stored (where stored starts at 0 and goes negative when leave is taken)
            stored_balance = float(leave_balance['annual_leave']) if leave_balance else 0.0
            calculated_annual_leave = float(accrued_annual_leave) + stored_balance
        else:
            calculated_annual_leave = 0

        if not leave_balance:
            print(f"Leave balance not found for user ID: {session['user_id']}")  # Debugging

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    # Add calendar data for employee view
    calendar_data = None
    leave_dates = {}
    if user_role != 'admin':
        import calendar as cal_module
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        try:
            month = datetime.now().month
            year = datetime.now().year
            
            # Fetch leave applications
            cur.execute('''
                SELECT * FROM leave_applications 
                WHERE user_id = %s 
                ORDER BY start_date
            ''', (session['user_id'],))
            user_leaves = cur.fetchall()
            
            # Build leave dates dictionary
            for leave in user_leaves:
                current_date = leave['start_date']
                end_date = leave['end_date']
                
                while current_date <= end_date:
                    date_key = current_date.strftime('%Y-%m-%d')
                    if date_key not in leave_dates:
                        leave_dates[date_key] = []
                    
                    leave_dates[date_key].append({
                        'type': leave['leave_type'],
                        'status': leave['status'],
                        'id': leave['id']
                    })
                    current_date += timedelta(days=1)
            
            calendar_data = {
                'calendar': cal_module.monthcalendar(year, month),
                'month': month,
                'year': year,
                'month_name': cal_module.month_name[month],
                'current_day': datetime.now().day,
                'current_month': datetime.now().month,
                'current_year': datetime.now().year
            }
        finally:
            cur.close()
            conn.close()

    return render_template('landing.html', 
                         employees=employees, 
                         leaves=leaves, 
                         leave_balance=leave_balance,
                         calculated_annual_leave=calculated_annual_leave,
                         user_role=user_role,
                         page=page,
                         total_pages=total_pages if user_role == 'admin' else 1,
                         calendar_data=calendar_data,
                         leave_dates=leave_dates)

# Add to add_employee_form route
@app.route('/add_employee_form')
def add_employee_form():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        abort(403)
    return render_template('add_employee.html')
# Edit Employee
@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Get existing employee data
        cur.execute('SELECT * FROM employees WHERE id = %s', (employee_id,))
        employee = cur.fetchone()

        if request.method == 'POST':
            # Get updated form data
            full_name = request.form['full_name']
            phone = request.form['phone']
            department = request.form['department']
            start_date = request.form['start_date']
            
            job_title = request.form['job_title']
            
            # Handle file upload
            profile_picture = employee['profile_picture']
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    profile_picture = filename

            # Update database
            cur.execute('''
                UPDATE employees SET
                full_name = %s,
                phone = %s,
                department = %s,
                job_title = %s,
                start_date = %s,
                profile_picture = %s
                WHERE id = %s
            ''', (full_name, phone, department, job_title, start_date, profile_picture, employee_id))
            
            conn.commit()
            
            # Log audit
            log_audit(session['user_id'], 'Edit Employee', 'Employee', employee_id, 
                     f"Updated details for employee ID {employee_id}")

            flash('Employee updated successfully!', 'success')
            return redirect(url_for('landing'))

        return render_template('edit_employee.html', employee=employee)

    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('landing'))
        
    finally:
        cur.close()
        conn.close()
        
# Delete Employee
@app.route('/delete_employee/<int:employee_id>')
def delete_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('DELETE FROM employees WHERE id = %s', (employee_id,))
        conn.commit()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('landing'))


@app.route('/promote-user/<int:user_id>', methods=['POST'])
def promote_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Verify current user is admin
        cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
        if cur.fetchone()[0] != 'admin':
            flash('Admin privileges required', 'error')
            return redirect(url_for('landing'))

        # Promote target user
        cur.execute('UPDATE users SET role = "admin" WHERE id = %s', (user_id,))
        conn.commit()
        flash('User promoted to admin', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Promotion failed: {str(e)}', 'error')
        
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('landing'))

    search_term = request.args.get('search', '').strip()

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Get filtered employees
                base_query = '''
                    SELECT e.*, u.username as creator 
                    FROM employees e
                    LEFT JOIN users u ON e.creator_id = u.id
                '''
                
                if search_term:
                    query = base_query + '''
                        WHERE e.full_name ILIKE %s
                        OR e.employee_id ILIKE %s
                        OR e.department ILIKE %s
                    '''
                    pattern = f'%{search_term}%'
                    cur.execute(query, (pattern, pattern, pattern))
                else:
                    cur.execute(base_query)

                employees = cur.fetchall()

                return render_template('admin_dashboard.html',
                                     employees=employees,
                                     search_term=search_term)

    except Exception as e:
        print(f"Search error: {str(e)}")
        flash('Error loading employees', 'error')
        return redirect(url_for('admin_dashboard'))




@app.route('/leave_calendar')
def leave_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from datetime import datetime, timedelta
    import calendar
    
    # Get month and year from query params, default to current
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        # Fetch all leave applications for the user
        cur.execute('''
            SELECT * FROM leave_applications 
            WHERE user_id = %s 
            ORDER BY start_date
        ''', (session['user_id'],))
        leaves = cur.fetchall()
        
        # Create calendar data structure
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        # Build a dictionary of dates with leave info
        leave_dates = {}
        for leave in leaves:
            current_date = leave['start_date']
            end_date = leave['end_date']
            
            # Add all dates in the leave range
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                if date_key not in leave_dates:
                    leave_dates[date_key] = []
                
                leave_dates[date_key].append({
                    'type': leave['leave_type'],
                    'status': leave['status'],
                    'id': leave['id']
                })
                current_date += timedelta(days=1)
        
        # Calculate previous and next month
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        # Get current date for highlighting today
        now = datetime.now()
        
        return render_template('leave_calendar.html',
                             calendar=cal,
                             month=month,
                             year=year,
                             month_name=month_name,
                             leave_dates=leave_dates,
                             prev_month=prev_month,
                             prev_year=prev_year,
                             next_month=next_month,
                             next_year=next_year,
                             current_day=now.day,
                             current_month=now.month,
                             current_year=now.year)
    finally:
        cur.close()
        conn.close()


@app.route('/admin/audit_logs')
def audit_logs():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute('''
            SELECT al.*, u.username as admin_name 
            FROM audit_logs al
            JOIN users u ON al.admin_id = u.id
            ORDER BY al.created_at DESC
        ''')
        logs = cur.fetchall()
        return render_template('audit_logs.html', logs=logs)
    except Exception as e:
        flash(f'Error loading audit logs: {e}', 'error')
        return redirect(url_for('landing'))
    finally:
        cur.close()
        conn.close()


@app.route('/admin/approve_leave/<int:leave_id>', methods=['POST'])
def approve_leave(leave_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    try:
        # Get leave application details
        cur.execute('SELECT * FROM leave_applications WHERE id = %s', (leave_id,))
        leave_app = cur.fetchone()
        
        if not leave_app:
            flash('Leave application not found.', 'error')
            return redirect(url_for('admin_leaves'))
        
        # Update leave status to Approved
        cur.execute("UPDATE leave_applications SET status = 'Approved' WHERE id = %s", (leave_id,))
        
        # Calculate leave days to deduct
        leave_type = leave_app['leave_type'].lower()
        
        # Use the stored total days from the application
        # This correctly handles partial days and multi-day requests
        days_to_deduct = float(leave_app['days'])
        
        # Deduct from appropriate leave balance
        if 'annual' in leave_type:
            cur.execute('''
                UPDATE leave_balance 
                SET annual_leave = annual_leave - %s 
                WHERE user_id = %s
            ''', (days_to_deduct, leave_app['user_id']))
        elif 'sick' in leave_type:
            cur.execute('''
                UPDATE leave_balance 
                SET sick_leave = sick_leave - %s 
                WHERE user_id = %s
            ''', (days_to_deduct, leave_app['user_id']))
        elif 'family' in leave_type:
            cur.execute('''
                UPDATE leave_balance 
                SET family_leave = family_leave - %s 
                WHERE user_id = %s
            ''', (days_to_deduct, leave_app['user_id']))
        
        # Log the action
        log_action('approve_leave', session['user_id'], leave_id, 'leave_application', 
                  f"Approved {days_to_deduct} days of {leave_type} leave")
        
        conn.commit()
        flash('Leave approved successfully and balance updated', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error approving leave: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin_leaves'))

@app.route('/admin/reject_leave/<int:leave_id>', methods=['POST'])
def reject_leave(leave_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    try:
        # Get leave details
        cur.execute("SELECT * FROM leave_applications WHERE id = %s", (leave_id,))
        leave = cur.fetchone()
        
        if not leave:
            flash('Leave application not found', 'error')
            return redirect(url_for('admin_dashboard'))

        if leave['status'] != 'Pending':
             flash('Can only reject pending leaves', 'error')
             return redirect(url_for('admin_dashboard'))

        # NOTE: No balance refund needed since balance is only deducted on approval

        # Update status
        cur.execute("UPDATE leave_applications SET status = 'Rejected' WHERE id = %s", (leave_id,))
        
        conn.commit()
        
        # Log audit
        leave_days = leave.get('days', 0)
        log_audit(session['user_id'], 'Reject Leave', 'Leave Application', leave_id, 
                 f"Rejected {leave['leave_type']} leave for {leave_days} days")
        
        flash('Leave rejected', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error rejecting leave: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin_leaves'))
    # Add new routes
@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    if request.method == 'POST':
        leave_type = request.form['leave_type']
        selected_dates = request.form.getlist('selected_dates[]')
        comments = request.form.get('comments', '')
        document_path = None

        # Handle file upload
        if 'document' in request.files:
            file = request.files['document']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                document_path = filename

        try:
            if not selected_dates:
                flash('Please select at least one date!', 'error')
                return redirect(url_for('employee_dashboard'))
            
            # Sort dates
            selected_dates.sort()
            start_date = selected_dates[0]
            end_date = selected_dates[-1]
            
            # Calculate total leave days
            total_leave_days = 0
            
            for date_str in selected_dates:
                # Check if this date has partial hours
                hours_key = f'hours_{date_str}'
                hours_str = request.form.get(hours_key, '')
                
                if hours_str:
                    # Partial day - hours off
                    try:
                        hours_off = float(hours_str)
                        if hours_off < 0 or hours_off > 8:
                            flash(f'Hours for {date_str} must be between 0 and 8!', 'error')
                            return redirect(url_for('employee_dashboard'))
                        
                        # Convert hours to days (e.g., 2 hours = 0.25 days)
                        total_leave_days += hours_off / 8.0
                    except ValueError:
                        flash(f'Invalid hours value for {date_str}!', 'error')
                        return redirect(url_for('employee_dashboard'))
                else:
                    # Full day
                    total_leave_days += 1.0
            
            if total_leave_days == 0:
                flash('No leave days calculated!', 'error')
                return redirect(url_for('employee_dashboard'))

            # NOTE: Balance is NOT deducted here - only when admin approves
            # This prevents double-deduction bug

            # Record application
            cur.execute('''
                INSERT INTO leave_applications 
                (user_id, leave_type, start_date, end_date, comments, document_path, days, hours_worked)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], leave_type, start_date, end_date, comments, document_path, total_leave_days, None))

            conn.commit()
            flash(f'Leave applied successfully! Total: {total_leave_days:.2f} days (Pending approval)', 'success')
            return redirect(url_for('employee_dashboard'))

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('employee_dashboard'))

        finally:
            cur.close()
            conn.close()

    return render_template('apply_leave.html')

@app.route('/leave/<int:leave_id>/comments', methods=['GET', 'POST'])
def leave_comments(leave_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if request.method == 'POST':
            comment_text = request.form.get('comment', '').strip()
            if comment_text:
                cur.execute('''
                    INSERT INTO leave_comments (leave_application_id, user_id, comment)
                    VALUES (%s, %s, %s)
                ''', (leave_id, session['user_id'], comment_text))
                conn.commit()
                flash('Comment added successfully!', 'success')
            return redirect(url_for('leave_comments', leave_id=leave_id))
        
        # GET: Fetch leave details and comments
        cur.execute('''
            SELECT l.*, u.username, e.full_name
            FROM leave_applications l
            JOIN users u ON l.user_id = u.id
            LEFT JOIN employees e ON l.user_id = e.user_id
            WHERE l.id = %s
        ''', (leave_id,))
        leave = cur.fetchone()
        
        if not leave:
            flash('Leave application not found!', 'error')
            return redirect(url_for('landing'))
        
        # Fetch comments
        cur.execute('''
            SELECT c.*, u.username, e.full_name
            FROM leave_comments c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN employees e ON c.user_id = e.user_id
            WHERE c.leave_application_id = %s
            ORDER BY c.created_at ASC
        ''', (leave_id,))
        comments = cur.fetchall()
        
        return render_template('leave_comments.html', leave=leave, comments=comments)
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('landing'))
    finally:
        cur.close()
        conn.close()


@app.route('/landing/cancel_leave/<int:leave_id>', methods=['POST'])
def cancel_leave(leave_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    try:
        # Get the leave application details
        cur.execute('SELECT * FROM leave_applications WHERE id = %s AND user_id = %s', 
                   (leave_id, session['user_id']))
        leave_app = cur.fetchone()
        
        if not leave_app:
            return jsonify({'success': False, 'message': 'Leave application not found'}), 404
        
        # Only allow canceling pending applications
        if leave_app['status'].lower() != 'pending':
            return jsonify({'success': False, 'message': f'Cannot cancel {leave_app["status"].lower()} leave'}), 400
        
        # Update status to Canceled
        cur.execute("UPDATE leave_applications SET status = 'Canceled' WHERE id = %s", (leave_id,))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Leave application canceled successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/holidays')
def admin_holidays():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('landing'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM public_holidays ORDER BY holiday_date DESC')
    holidays = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin_holidays.html', holidays=holidays)

@app.route('/admin/holidays/add', methods=['POST'])
def add_holiday():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('landing'))
    
    holiday_name = request.form.get('holiday_name')
    holiday_date = request.form.get('holiday_date')
    is_recurring = request.form.get('is_recurring') == 'on'
    
    if not holiday_name or not holiday_date:
        flash('Name and date are required', 'error')
        return redirect(url_for('admin_holidays'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT INTO public_holidays (holiday_name, holiday_date, is_recurring)
            VALUES (%s, %s, %s)
        ''', (holiday_name, holiday_date, is_recurring))
        
        conn.commit()
        flash('Holiday added successfully', 'success')
        
        log_audit(session['user_id'], 'Add Holiday', 'Public Holiday', None, 
                 f"Added holiday: {holiday_name} on {holiday_date}")
                 
    except Exception as e:
        conn.rollback()
        flash(f'Error adding holiday: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('admin_holidays'))

@app.route('/admin/holidays/delete/<int:holiday_id>', methods=['POST'])
def delete_holiday(holiday_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('landing'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('DELETE FROM public_holidays WHERE id = %s', (holiday_id,))
        conn.commit()
        flash('Holiday deleted successfully', 'success')
        
        log_audit(session['user_id'], 'Delete Holiday', 'Public Holiday', holiday_id, 
                 "Deleted public holiday")
                 
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting holiday: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('admin_holidays'))

if __name__ == '__main__':
    app.run(debug=True)
