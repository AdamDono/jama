from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from werkzeug.utils import secure_filename  # <-- Add this

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
    conn = psycopg2.connect(**DATABASE)
    return conn

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
        cur = conn.cursor()
        
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
        cur = conn.cursor()
        
        try:
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            
            if user and check_password_hash(user[3], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
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
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = None
        cur = None
        try:
            # Get form data
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            employee_id = request.form.get('employee_id')
            start_date = request.form.get('start_date')
            department = request.form.get('department')

            # Validate required fields
            if not all([full_name, phone, employee_id, start_date, department]):
                flash('All fields except profile picture are required!', 'error')
                return redirect(url_for('add_employee'))

            # Handle file upload
            profile_picture = None
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_picture = filename

            conn = get_db_connection()
            cur = conn.cursor()

            # Check duplicates
            cur.execute('''
                SELECT * FROM employees 
                WHERE phone = %s OR employee_id = %s
            ''', (phone, employee_id))
            
            if cur.fetchone():
                flash('Phone or Employee ID already exists!', 'error')
                return redirect(url_for('add_employee'))

            # Insert employee
            cur.execute('''
                INSERT INTO employees 
                (user_id, full_name, phone, employee_id, start_date, department, profile_picture)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], full_name, phone, employee_id, start_date, department, profile_picture))

            conn.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('landing'))

        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_employee'))

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    # GET request
    return render_template('add_employee.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/landing')
def landing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('landing.html')


