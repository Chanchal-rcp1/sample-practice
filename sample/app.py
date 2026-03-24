from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "users.db"

# -----------------------------
# Default Admin Credentials
# -----------------------------
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"


# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Initialize Database
# -----------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)
    # NEW: SECTIONS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT
        )
    """)

    # NEW: CONTENT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            title TEXT,
            type TEXT,
            link TEXT,
            description TEXT,
            FOREIGN KEY(section_id) REFERENCES sections(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


@app.route('/guidance')
def guidance():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sections")
    sections = cursor.fetchall()

    conn.close()

    return render_template("guidance.html", sections=sections)

@app.route('/guidance/<int:id>')
def guidance_section(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sections WHERE id=?", (id,))
    section = cursor.fetchone()

    cursor.execute("SELECT * FROM content WHERE section_id=?", (id,))
    content = cursor.fetchall()

    conn.close()

    return render_template("guidance_section.html", section=section, content=content)

@app.route('/manage_sections')
def manage_sections():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sections")
    sections = cursor.fetchall()
    
    conn.close()
    
    return render_template("manage_sections.html", sections=sections)

@app.route('/manage_content')
def manage_content():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM content")
    content = cursor.fetchall()
    
    cursor.execute("SELECT * FROM sections")
    sections = cursor.fetchall()
    
    conn.close()
    
    return render_template("manage_content.html", content=content, sections=sections)

@app.route('/add_section', methods=['POST'])
def add_section():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO sections (name, description) VALUES (?, ?)",
        (request.form['name'], request.form['description'])
    )

    conn.commit()
    conn.close()

    return redirect('/manage_sections')

@app.route('/add_content', methods=['POST'])
def add_content():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO content (section_id, title, type, link, description)
    VALUES (?, ?, ?, ?, ?)
    """, (
        request.form['section_id'],
        request.form['title'],
        request.form['type'],
        request.form['link'],
        request.form['description']
    ))

    conn.commit()
    conn.close()

    return redirect('/manage_content')
# -----------------------------
# Create Default Admin
# -----------------------------
def create_admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (ADMIN_EMAIL,))
    admin = cursor.fetchone()

    if admin is None:
        hashed_password = generate_password_hash(ADMIN_PASSWORD)

        cursor.execute(
            "INSERT INTO users (email,password,role) VALUES (?,?,?)",
            (ADMIN_EMAIL, hashed_password, "admin")

        )

        conn.commit()

    conn.close()


# Run database setup
init_db()
create_admin()


# -----------------------------
# Routes
# -----------------------------

# Home Page
@app.route('/')
def home():
    return render_template("home.html")


# -------- Login Page --------
@app.route('/login')
def login_page():
    return render_template("login.html")


# -------- Register Page --------
@app.route('/register')
def register_page():
    return render_template("register.html")


# -------- Register Logic --------
@app.route('/register', methods=['POST'])
def register():

    email = request.form['email']
    password = generate_password_hash(request.form['password'])

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (email,password,role) VALUES (?,?,?)",
            (email, password, "user")
        )
        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return "User already exists"

    conn.close()

    # After register go to login
    return redirect('/login')


# -------- Login Logic --------
@app.route('/login', methods=['POST'])
def login():

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    conn.close()

    if user and check_password_hash(user['password'], password):

        session['user_id'] = user['id']
        session['email'] = user['email']
        session['role'] = user['role']

        if user['role'] == "admin":
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('account'))

    return "Invalid Email or Password"


# -------- User Dashboard --------
@app.route('/account')
def account():

    if 'user_id' in session:

        return render_template(
            "account.html",
            email=session['email'],
            role=session['role']
        )

    return redirect('/login')


# -------- Admin Dashboard --------
@app.route('/admin')
def admin_dashboard():

    if 'role' in session and session['role'] == "admin":

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id,email,role FROM users")
        users = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        conn.close()

        return render_template(
            "admin.html",
            email=session['email'],
            users=users,
            total_users=total_users,
            
        )

    return redirect('/login')
# -------- Forgot Password Page + Logic --------
@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['reset_email'] = email
            return redirect('/reset_password')

        return "Email not found"

    return render_template("forgot_password.html")

# -------- Reset Password Page --------
@app.route('/reset_password')
def reset_password_page():

    if 'reset_email' not in session:
        return redirect('/login')

    return render_template("reset_password.html")


# -------- Reset Password Logic --------
@app.route('/reset_password', methods=['POST'])
def reset_password():

    if 'reset_email' not in session:
        return redirect('/login')

    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        return "Passwords do not match"

    hashed_password = generate_password_hash(new_password)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=? WHERE email=?",
        (hashed_password, session['reset_email'])
    )

    conn.commit()
    conn.close()

    session.pop('reset_email', None)

    return redirect('/login')

# -------- Logout --------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)