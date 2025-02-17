from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

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


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/landing')
def landing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('landing.html')