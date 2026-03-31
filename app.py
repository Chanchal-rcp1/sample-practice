from flask import Flask, flash, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "placement_secret"

# -----------------------------
# ADMIN FIXED CREDENTIALS
# -----------------------------
ADMIN_EMAIL = "admin@123"
ADMIN_PASSWORD = "admin123"

# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # CONTENT TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            content_type TEXT,
            content_link TEXT
        )
    """)

    # PROGRESS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT,
            section TEXT,
            percentage INTEGER
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        # ADMIN LOGIN
        if role == "admin":

            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                return redirect("/admin_dashboard")

            return "Invalid Admin Credentials"

        # STUDENT LOGIN
        elif role == "student":

            conn = sqlite3.connect("database.db")
            cur = conn.cursor()

            cur.execute(
                "SELECT * FROM users WHERE email=? AND password=? AND role='student'",
                (email,password)
            )

            user = cur.fetchone()
            conn.close()

            if user:
                session["student"] = email
                return redirect("/student_dashboard")

            return "Account not found. Please register first."

    return render_template("login.html")
#-----------------------------
# Home PAGE
#-----------------------------
@app.route("/")
def home():
    return render_template("home.html")

#-----------------------------

@app.route("/delete_student/<email>", methods=["POST"])
def delete_student(email):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    flash("Student deleted successfully!", "success")

    return redirect(url_for("view_students"))

# -----------------------------
# REGISTER
# -----------------------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        try:

            cur.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name,email,password,"student")
            )

            conn.commit()

        except:
            conn.close()
            return "Email already exists!"

        conn.close()
        return redirect("/")

    return render_template("register.html")

# -----------------------------
# STUDENT DASHBOARD
# -----------------------------
@app.route("/student_dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect("/")
    return render_template("student_dashboard.html")

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin_dashboard")
def admin_dashboard():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM content")
    total_resources = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM progress WHERE percentage <= 30")
    beginner = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM progress WHERE percentage > 30 AND percentage <= 70")
    intermediate = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM progress WHERE percentage > 70")
    ready = cur.fetchone()[0]
    total = beginner + intermediate + ready
    if total == 0:
      beginner_percent = 0
      intermediate_percent = 0
      ready_percent = 0
    else:
      beginner_percent = int((beginner / total) * 100)
      intermediate_percent = int((intermediate / total) * 100)
      ready_percent = int((ready / total) * 100)
    

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_resources=total_resources,
        beginner=beginner,
        intermediate=intermediate,
        ready=ready,
        beginner_percent=beginner_percent,
        intermediate_percent=intermediate_percent,
        ready_percent=ready_percent
    )

# -----------------------------
# VIEW STUDENTS
# -----------------------------
@app.route("/view_students")
def view_students():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT name,email FROM users WHERE role='student'")
    students = cur.fetchall()

    conn.close()

    return render_template("view_students.html",students=students)

# -----------------------------
# MANAGE CONTENT
# -----------------------------
@app.route("/manage_content")
def manage_content():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM content")
    contents = cur.fetchall()

    conn.close()

    return render_template("manage_content.html",contents=contents)

# -----------------------------
# DELETE CONTENT
# -----------------------------
@app.route("/delete_content/<int:id>")
def delete_content(id):

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM content WHERE id=?",(id,))
    conn.commit()

    conn.close()

    return redirect("/manage_content")
# -----------------------------
# EDIT CONTENT
# -----------------------------
@app.route("/edit_content/<int:id>", methods=["GET", "POST"])
def edit_content(id):

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title").strip().lower()
        content_type = request.form.get("content_type")
        content_link = request.form.get("content_link")

        cur.execute("""
            UPDATE content
            SET title=?, content_type=?, content_link=?
            WHERE id=?
        """, (title, content_type, content_link, id))

        conn.commit()
        conn.close()
        return redirect("/manage_content")

    # GET request
    cur.execute("SELECT * FROM content WHERE id=?", (id,))
    data = cur.fetchone()
    conn.close()

    return render_template("edit_content.html", data=data)


# -----------------------------
# SELECT CATEGORY
# -----------------------------
@app.route("/select_category")
def select_category():
    return render_template("select_category.html")

# -----------------------------
# ADD CONTENT
# -----------------------------
@app.route("/add_content/<category>", methods=["GET","POST"])
def add_content(category):

    if request.method == "POST":

        title = request.form.get("title").strip().lower()
        content_type = request.form.get("content_type")
        content_link = request.form.get("content_link")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO content (category,title,content_type,content_link)
            VALUES (?,?,?,?)
        """,(category,title,content_type,content_link))

        conn.commit()
        conn.close()

        return redirect("/admin_dashboard")

    return render_template("add_content.html",category=category)

# -----------------------------
# VIEW CONTENT
# -----------------------------
@app.route("/content/<category>")
def view_content(category):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM content WHERE category=?",
        (category,)
    )

    contents = cur.fetchall()
    conn.close()

    return render_template("view_content.html",
                           contents=contents,
                           category=category)

# -----------------------------
# TECHNICAL PAGE
# -----------------------------
@app.route("/technical")
def technical():

    student = session.get("student")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT percentage FROM progress
    WHERE student_email=? AND section='datastructures'
    """,(student,))

    data = cur.fetchone()

    progress = 0
    if data:
        progress = data[0]

    conn.close()

    return render_template("technical.html", progress=progress)

# -----------------------------
# APTITUDE CONTENT
# -----------------------------
@app.route("/aptitude")
def aptitude():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM content WHERE category='aptitude'")
    contents = cur.fetchall()

    # 🔥 FIX (IMPORTANT)
    cleaned_contents = []
    for c in contents:
        cleaned_contents.append({
            "title": c["title"].strip().lower(),
            "content_type": c["content_type"].strip(),
            "content_link": c["content_link"].strip()
        })

    conn.close()

    return render_template("aptitude.html", contents=cleaned_contents)
# OTHER PAGES
# -----------------------------
@app.route("/interview-skills")
def interview_skills():
    return render_template("interview_skills.html")

@app.route("/online_profile")
def online_profile():
    return render_template("online_profile.html")

@app.route("/resume_form")
def resume_form():
    return render_template("ai_resume_builder.html")

# -----------------------------
# GENERATE RESUME
# -----------------------------
@app.route("/generate_resume", methods=["POST"])
def generate_resume():

    session["name"] = request.form.get("name")
    session["email"] = request.form.get("email")
    session["phone"] = request.form.get("phone")
    session["skills"] = request.form.get("skills")
    session["education"] = request.form.get("education")
    session["experience"] = request.form.get("experience")

    photo = request.files.get("photo")

    if photo and photo.filename != "":

        upload_folder = "static/uploads"

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        filepath = os.path.join(upload_folder, photo.filename)
        photo.save(filepath)

        session["photo"] = filepath

    else:
        session["photo"] = ""

    return render_template("ai_loading.html")

# -----------------------------
# AI ANALYSIS PAGE
# -----------------------------
@app.route("/show_analysis")
def show_analysis():

    photo = session.get("photo")
    name = session.get("name")
    email = session.get("email")
    phone = session.get("phone")
    skills = session.get("skills","")

    weak_areas = []

    if "python" not in skills.lower():
        weak_areas.append("Python Programming")

    if "sql" not in skills.lower():
        weak_areas.append("Database / SQL")

    if "data structures" not in skills.lower() and "dsa" not in skills.lower():
        weak_areas.append("Data Structures")

    score = 100 - (len(weak_areas) * 20)

    if score < 0:
        score = 0

    return render_template(
        "ai_analysis.html",
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        weak_areas=weak_areas,
        score=score,
        photo=photo
    )

# -----------------------------
# PROGRESS UPDATE
# -----------------------------
@app.route("/complete_topic")
def complete_topic():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # 🔥 RANDOM PROGRESS (for testing categories)
    import random

    users = ["a@gmail.com", "b@gmail.com", "c@gmail.com", "d@gmail.com"]

    for user in users:
        percent = random.randint(0, 100)

        cur.execute("""
            INSERT INTO progress (student_email, section, percentage)
            VALUES (?,?,?)
        """, (user, "datastructures", percent))

    conn.commit()
    conn.close()

    return "Dummy Data Inserted!"

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)