from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from werkzeug.utils import secure_filename  # <-- Add this
from psycopg2.extras import DictCursor 
import psycopg2.extras  # Add this line

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
        cur = conn.cursor(cursor_factory=DictCursor)  # Add this
        
        try:
            cur.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
            if cur.fetchone():
                flash('Username or email already exists!', 'error')
                return redirect(url_for('signup'))
            
            hashed_password = generate_password_hash(password)
            
            # Corrected line below
            cur.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password)
            )  # This closing parenthesis was missing
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
    try:
        # CREATE CURSOR ONCE WITH DictCursor
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('''
            SELECT * FROM employees 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        ''', (session['user_id'],))
        employees = cur.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        employees = []
    finally:
        cur.close()
        conn.close()
    
    return render_template('landing.html', employees=employees)


@app.route('/add_employee_form')
def add_employee_form():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
