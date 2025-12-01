from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from werkzeug.utils import secure_filename  # <-- Add this
from psycopg2.extras import DictCursor 
import psycopg2.extras  # Add this line
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_annual_leave(start_date):
    """
    Calculate annual leave accrual based on start date.
    Accrues at 1.7 days per month (approximately 0.0567 days per day).
    """
    from datetime import datetime
    
    if not start_date:
        return 0
    
    # Convert to date object if string
    now = datetime.now().date()
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # Calculate total days elapsed
    days_elapsed = (now - start_date).days
    
    # If negative (future date), return 0
    if days_elapsed < 0:
        return 0
    
    # Calculate accrued leave: 1.7 days per month = 1.7/30 days per day
    # This equals approximately 0.0567 days per day
    daily_accrual_rate = 1.7 / 30.0
    accrued_leave = days_elapsed * daily_accrual_rate
    
    return round(accrued_leave, 2)


DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
     'port': '5433',  
}


def get_db_connection():
 
    return psycopg2.connect(**DATABASE)


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
            (user_id, full_name, phone, employee_id, start_date, department, profile_picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (new_user_id, full_name, phone, employee_id, start_date, department, profile_picture))
        
        # Create leave balance (0 annual, 30 sick, 3 family)
        cur.execute('''
            INSERT INTO leave_balance (user_id, annual_leave, sick_leave, family_leave, unpaid_leave)
            VALUES (%s, %s, %s, %s, %s)
        ''', (new_user_id, 0, 30, 3, 0))
        
        conn.commit()
        flash(f'Employee added! Login: {full_name} / Password: {employee_id} (must change on first login)', 'success')
        return redirect(url_for('landing'))

    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('show_add_form'))
    
    finally:
        cur.close()
        conn.close()

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if request.method == 'POST':
            # Handle profile update
            full_name = request.form['full_name']
            phone = request.form['phone']
            department = request.form['department']
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
                SET full_name = %s, phone = %s, department = %s, profile_picture = %s
                WHERE user_id = %s
            ''', (full_name, phone, department, profile_picture, session['user_id']))
            
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
            # Calculate accrued leave
            accrued_annual_leave = calculate_annual_leave(employee['start_date'])
            # Add stored balance (can be negative)
            stored_balance = leave_balance['annual_leave'] if leave_balance else 0
            calculated_annual_leave = accrued_annual_leave + stored_balance
        
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


@app.route('/landing')
def landing():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Initialize variables
    employees = []
    leaves = []
    leave_balance = None
    calculated_annual_leave = 0

    try:
        # Fetch the user's role
        cur.execute('SELECT role FROM users WHERE id = %s', (session['user_id'],))
        user_role = cur.fetchone()['role']

        # Fetch employees based on role
        if user_role == 'admin':
            cur.execute('SELECT * FROM employees ORDER BY created_at DESC')
            employees = cur.fetchall()
        else:
            cur.execute('SELECT * FROM employees WHERE user_id = %s ORDER BY created_at DESC', (session['user_id'],))
            employees = cur.fetchall()

            # Fetch the user's leave applications
            cur.execute('''
                SELECT * FROM leave_applications 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (session['user_id'],))
            leaves = cur.fetchall()

        # Fetch the user's leave balance
        cur.execute('SELECT * FROM leave_balance WHERE user_id = %s', (session['user_id'],))
        leave_balance = cur.fetchone()
        
        # Get employee start date to calculate annual leave
        cur.execute('SELECT start_date FROM employees WHERE user_id = %s', (session['user_id'],))
        employee = cur.fetchone()
        
        if employee and employee['start_date']:
            # Calculate accrued leave based on start date
            accrued_annual_leave = calculate_annual_leave(employee['start_date'])
            # Add the stored balance (which tracks deductions and can be negative)
            # Net = Accrued + Stored (where stored starts at 0 and goes negative when leave is taken)
            stored_balance = leave_balance['annual_leave'] if leave_balance else 0
            calculated_annual_leave = accrued_annual_leave + stored_balance
        else:
            calculated_annual_leave = 0

        if not leave_balance:
            print(f"Leave balance not found for user ID: {session['user_id']}")  # Debugging

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    return render_template('landing.html', 
                         employees=employees, 
                         leaves=leaves, 
                         leave_balance=leave_balance,
                         calculated_annual_leave=calculated_annual_leave,
                         user_role=user_role)

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
                start_date = %s,
                profile_picture = %s
                WHERE id = %s
            ''', (full_name, phone, department, start_date, profile_picture, employee_id))
            
            conn.commit()
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

@app.route('/admin/leaves')
def admin_leaves():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('landing'))

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Fetch pending leaves using robust LEFT JOIN
                cur.execute('''
                    SELECT l.*, COALESCE(e.full_name, u.username) as full_name
                    FROM leave_applications l
                    LEFT JOIN employees e ON l.user_id = e.user_id
                    JOIN users u ON l.user_id = u.id
                    WHERE l.status = 'pending'
                    ORDER BY l.created_at ASC
                ''')
                pending_leaves = cur.fetchall()
                
                return render_template('admin_leaves.html', pending_leaves=pending_leaves)
    except Exception as e:
        print(f"Error loading leaves: {str(e)}")
        flash('Error loading leave applications', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_leave/<int:leave_id>', methods=['POST'])
def approve_leave(leave_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("UPDATE leave_applications SET status = 'Approved' WHERE id = %s", (leave_id,))
        conn.commit()
        flash('Leave approved successfully', 'success')
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
        # Get leave details to refund balance
        cur.execute("SELECT * FROM leave_applications WHERE id = %s", (leave_id,))
        leave = cur.fetchone()
        
        if not leave:
            flash('Leave application not found', 'error')
            return redirect(url_for('admin_dashboard'))

        if leave['status'] != 'pending':
             flash('Can only reject pending leaves', 'error')
             return redirect(url_for('admin_dashboard'))

        # Calculate days to refund
        leave_days = (leave['end_date'] - leave['start_date']).days + 1
        leave_type = leave['leave_type']

        # Refund balance
        cur.execute(f'''
            UPDATE leave_balance 
            SET {leave_type}_leave = {leave_type}_leave + %s
            WHERE user_id = %s
        ''', (leave_days, leave['user_id']))

        # Update status
        cur.execute("UPDATE leave_applications SET status = 'Rejected' WHERE id = %s", (leave_id,))
        
        conn.commit()
        flash('Leave rejected and balance refunded', 'success')

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
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        comments = request.form.get('comments', '')
        document_path = None

        # Handle file upload (keep existing)
        if 'document' in request.files:
            file = request.files['document']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                document_path = filename

        try:
            # Calculate leave days (keep existing)
            from datetime import datetime, timedelta
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Validation: Check if start or end date is weekend
            if start.weekday() >= 5 or end.weekday() >= 5:
                flash('Leave cannot start or end on a weekend!', 'error')
                return redirect(url_for('apply_leave'))

            # Calculate working days
            leave_days = 0
            current_day = start
            while current_day <= end:
                if current_day.weekday() < 5: # 0-4 are Mon-Fri
                    leave_days += 1
                current_day += timedelta(days=1)
            
            if leave_days == 0:
                flash('No working days selected!', 'error')
                return redirect(url_for('apply_leave'))

            # ===== NEW VALIDATION =====
            if leave_type == 'unpaid':
                 cur.execute(f'''
                    UPDATE leave_balance 
                    SET unpaid_leave = unpaid_leave + %s
                    WHERE user_id = %s
                ''', (leave_days, session['user_id']))
            else:
                # Update with NO floor (allow negative)
                cur.execute(f'''
                    UPDATE leave_balance 
                    SET {leave_type}_leave = {leave_type}_leave - %s
                    WHERE user_id = %s
                ''', (leave_days, session['user_id']))
            # ===== END NEW CODE =====

            # Record application (keep existing)
            cur.execute('''
                INSERT INTO leave_applications 
                (user_id, leave_type, start_date, end_date, comments, document_path, days)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], leave_type, start_date, end_date, comments, document_path, leave_days))

            conn.commit()
            flash('Leave applied successfully!', 'success')
            return redirect(url_for('landing'))

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('apply_leave'))

        finally:
            cur.close()
            conn.close()

    return render_template('apply_leave.html')
@app.route('/landing/cancel_leave/<int:leave_id>', methods=['POST'])
def cancel_leave(leave_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Debugging: Log the leave_id and user_id
        print(f"Attempting to cancel leave ID: {leave_id} for user ID: {session['user_id']}")

        # Check if the leave application belongs to the logged-in user and is pending
        cur.execute('''
            SELECT * FROM leave_applications 
            WHERE id = %s AND user_id = %s AND status = 'pending'
        ''', (leave_id, session['user_id']))
        leave = cur.fetchone()

        if not leave:
            print(f"Leave application not found or cannot be canceled. Leave ID: {leave_id}, User ID: {session['user_id']}")
            return jsonify({'success': False, 'message': 'Leave application not found or cannot be canceled'}), 404

        print(f"Leave application found: {leave}")

        cur.execute('DELETE FROM leave_applications WHERE id = %s', (leave_id,))
        conn.commit()

        print("Leave application canceled successfully")
        return jsonify({'success': True, 'message': 'Leave application canceled successfully'})

    except Exception as e:
        conn.rollback()
        print(f"Error canceling leave application: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        cur.close()
        conn.close()