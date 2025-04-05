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

# Database configuration
DATABASE = {
    'dbname': 'jama',
    'user': 'postgres',
    'password': 'Fliph106',
    'host': 'localhost',
     'port': '5433',  # Or correct port
}


def get_db_connection():
 
    return psycopg2.connect(**DATABASE)

# Create users table if it does not exist
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


# Create employees table
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
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        try:
            # Check if username or email already exists
            cur.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
            if cur.fetchone():
                flash('Username or email already exists!', 'error')
                return redirect(url_for('signup'))

            # Insert new user
            hashed_password = generate_password_hash(password)
            cur.execute('''
                INSERT INTO users (username, email, password)
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (username, email, hashed_password))
            user_id = cur.fetchone()['id']

            # Initialize leave balance for the new user
            cur.execute('''
                INSERT INTO leave_balance (user_id, annual_leave, sick_leave, family_leave)
                VALUES (%s, 15, 30, 3)
            ''', (user_id,))
            conn.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            flash('Registration failed!', 'error')
            return redirect(url_for('signup'))

        finally:
            cur.close()
            conn.close()

    return render_template('signup.html')
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
                flash('Login successful!', 'success')
                return redirect(url_for('landing'))
            else:
                flash('Invalid credentials!', 'error')
                return redirect(url_for('login'))
                
        finally:
            cur.close()
            conn.close()
            
    return render_template('login.html')

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
        profile_picture = None

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT * FROM employees WHERE phone=%s OR employee_id=%s', (phone, employee_id))
        if cur.fetchone():
            flash('Phone/ID already exists!', 'error')
            return redirect(url_for('show_add_form'))

        cur.execute('''
            INSERT INTO employees 
            (user_id, full_name, phone, employee_id, start_date, department, profile_picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], full_name, phone, employee_id, start_date, department, profile_picture))
        
        conn.commit()
        flash('Employee added!', 'success')
        return redirect(url_for('landing'))

    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('show_add_form'))
    
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

    try:
        # Get leave balance - ensure this query matches your database schema
        cur.execute('''
            SELECT annual_leave, sick_leave, family_leave 
            FROM leave_balance 
            WHERE user_id = %s
        ''', (session['user_id'],))
        leave_balance = cur.fetchone() or {
            'annual_leave': 15,  # Default values if not found
            'sick_leave': 30,
            'family_leave': 3
        }

        # Get leave applications
        cur.execute('''
            SELECT * FROM leave_applications 
            WHERE user_id = %s 
            ORDER BY start_date DESC
        ''', (session['user_id'],))
        leaves = cur.fetchall()

        return render_template('landing.html',
            leave_balance=leave_balance,
            leaves=leaves,
            user_role=session.get('role', 'employee')
        )

    except Exception as e:
        print(f"Database error: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('login'))
        
    finally:
        cur.close()
        conn.close()
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
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            leave_days = (end - start).days + 1

            # ===== NEW VALIDATION =====
            # Check current balance
            cur.execute(f'SELECT {leave_type}_leave FROM leave_balance WHERE user_id = %s', 
                       (session['user_id'],))
            current_balance = cur.fetchone()[f'{leave_type}_leave']

            # Prevent negative balances
            if leave_days > current_balance:
                flash(f'Not enough {leave_type} leave! Available: {current_balance} days', 'error')
                return redirect(url_for('apply_leave'))

            # Update with zero floor
            cur.execute(f'''
                UPDATE leave_balance 
                SET {leave_type}_leave = GREATEST(0, {leave_type}_leave - %s)
                WHERE user_id = %s
            ''', (leave_days, session['user_id']))
            # ===== END NEW CODE =====

            # Record application (keep existing)
            cur.execute('''
                INSERT INTO leave_applications 
                (user_id, leave_type, start_date, end_date, comments, document_path)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], leave_type, start_date, end_date, comments, document_path))

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

        # Debugging: Log the leave application details
        print(f"Leave application found: {leave}")

        # Delete the leave application
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