from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
import string
app = Flask(__name__)
app.secret_key = "supersecretkey"
from datetime import datetime, timedelta



# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT,
            role TEXT
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        description TEXT,
        processing_days INTEGER,
        fee INTEGER,
        required_documents TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER,
        user_email TEXT,

        name TEXT,
        gender TEXT,
        dob TEXT,
        age INTEGER,
        photo TEXT,

        present_house_no TEXT,
        present_house_name TEXT,
        present_locality TEXT,
        present_post_office TEXT,
        present_pincode TEXT,
        present_district TEXT,

        father_name TEXT,
        category TEXT,

        status TEXT,
        applied_date TEXT,
        due_date TEXT
    )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default services (clear first for testing)
    cursor.execute("DELETE FROM services")
    cursor.execute("""
    INSERT INTO services 
    (service_name, description, processing_days, fee, required_documents)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "Income Certificate",
        "Apply for income certificate",
        7,
        15,
        "Aadhar Card, Ration Card, Salary Certificate, Tax Receipt"
    ))

    cursor.execute("""
    INSERT INTO services 
    (service_name, description, processing_days, fee, required_documents)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "Community Certificate",
        "Apply for community certificate",
        10,
        20,
        "Aadhar Card, Old Community Certificate, School Record"
    ))

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route('/')
def home():
    return render_template('home.html')




# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, password, role)
        )
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    # Generate captcha when page loads
    if request.method == 'GET':
        captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        session['captcha'] = captcha
        return render_template('login.html', captcha=captcha)

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_captcha = request.form['captcha']

        # Check captcha first
        if user_captcha != session.get('captcha'):
            return "Invalid CAPTCHA"

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_email'] = user[2]
            session['role'] = user[4]

            if user[4] == "citizen":
                return redirect('/citizen_dashboard')
            elif user[4] == "officer":
                return redirect('/officer_dashboard')

        else:
            return "Invalid Credentials"
    return render_template('login.html')
# ---------------- FORGOT PASSWORD ----------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

            if request.method == 'POST':
                email = request.form['email']
                new_password = request.form['new_password']

                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET password=? WHERE email=?",
                    (new_password, email)
                )
                conn.commit()
                conn.close()

                return redirect('/login')

            return render_template('forgot_password.html')

# ---------------- CITIZEN DASHBOARD ---------------#
@app.route('/citizen_dashboard')
def citizen_dashboard():
    if 'user_email' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM services")
    services = cursor.fetchall()
    cursor.execute('''
    SELECT applications.id, 
       services.service_name, 
       applications.status,
       applications.applied_date,
       applications.due_date
        FROM applications
        JOIN services ON applications.service_id = services.id
        WHERE applications.user_email=?
    ''', (session['user_email'],))


    my_apps = cursor.fetchall()
    today = datetime.now().date()

    updated_apps = []

    for app in my_apps:
        app_id, service_name, status, applied_date, due_date = app

        if due_date:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_left = (due_date_obj - today).days
        else:
            days_left = None

        updated_apps.append((app_id, service_name, status, applied_date, due_date, days_left))

    my_apps = updated_apps
    conn.close()

    return render_template("citizen_dashboard.html",
                           services=services,
                           my_apps=my_apps)

@app.route('/timeline/<int:app_id>')
def timeline(app_id):
    if 'user_email' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Verify this application belongs to logged user
    cursor.execute(
        "SELECT id FROM applications WHERE id=? AND user_email=?",
        (app_id, session['user_email'])
    )
    app_check = cursor.fetchone()

    if not app_check:
        conn.close()
        return "Unauthorized Access"


    # Get logs
    cursor.execute(
        "SELECT action, timestamp FROM application_logs WHERE application_id=? ORDER BY timestamp ASC",
        (app_id,)
    )

    logs = cursor.fetchall()
    conn.close()

    return render_template("timeline.html", logs=logs)


# ---------------- OFFICER DASHBOARD ----------------
@app.route('/officer_dashboard')
def officer_dashboard():
    if 'role' not in session or session['role'] != "officer":
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
      SELECT applications.id,
             applications.user_email,
             services.service_name,
             applications.status,
             applications.applied_date,
             applications.due_date
      FROM applications
      JOIN services ON applications.service_id = services.id
    ''')

    apps = cursor.fetchall()

    today = datetime.now().date()
    applications = []

    for app in apps:
        app_id, user_email, service_name, status, applied_date, due_date = app

        if due_date:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_left = (due_date_obj - today).days
        else:
            days_left = None

        applications.append(
            (app_id, user_email, service_name, status,
             applied_date, due_date, days_left)
        )

    # Analytics
    cursor.execute("SELECT COUNT(*) FROM applications")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Approved'")
    approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Rejected'")
    rejected = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM applications
        WHERE status IN ('Pending','Under Review')
        AND due_date < date('now')
        """)
    overdue = cursor.fetchone()[0]
    conn.close()

    return render_template(
        'officer_dashboard.html',
        applications=applications,
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected
    )

# ---------------- APPLY SERVICE ----------------
@app.route('/apply/<int:service_id>', methods=['GET', 'POST'])
def apply(service_id):

    if 'user_email' not in session:
        return redirect('/login')

    if request.method == 'POST':

        name = request.form['name']
        gender = request.form['gender']
        dob = request.form['dob']
        age = request.form['age']

        present_house_no = request.form['present_house_no']
        present_house_name = request.form['present_house_name']
        present_locality = request.form['present_locality']
        present_post_office = request.form['present_post_office']
        present_pincode = request.form['present_pincode']
        present_district = request.form['present_district']

        father_name = request.form['father_name']
        category = request.form['category']

        photo = request.files['photo']
        photo_filename = photo.filename
        photo.save('static/uploads/' + photo_filename)

        applied_date = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT processing_days FROM services WHERE id=?", (service_id,))
        service_data = cursor.fetchone()

        processing_days = service_data[0]
        due_date = (datetime.now() + timedelta(days=processing_days)).strftime("%Y-%m-%d")



        cursor.execute("""
        INSERT INTO applications (
            service_id, user_email,
            name, gender, dob, age, photo,
            present_house_no, present_house_name, present_locality,
            present_post_office, present_pincode, present_district,
            father_name, category,
            status, applied_date, due_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            service_id, session['user_email'],
            name, gender, dob, age, photo_filename,
            present_house_no, present_house_name, present_locality,
            present_post_office, present_pincode, present_district,
            father_name, category,
            "Pending", applied_date, due_date
        ))

        application_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO application_logs (application_id, action) VALUES (?, ?)",
            (application_id, "Application Submitted")
        )

        conn.commit()
        conn.close()

        return redirect('/citizen_dashboard')

    return render_template("application_form.html")

# ---------------- APPROVE / REJECT ----------------
@app.route('/approve/<int:app_id>')
def approve(app_id):
    if 'role' not in session or session['role'] != "officer":
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Update status
    cursor.execute(
        "UPDATE applications SET status='Approved' WHERE id=?",
        (app_id,)
    )

    # Insert timeline log
    cursor.execute(
        "INSERT INTO application_logs (application_id, action) VALUES (?, ?)",
        (app_id, "Application Approved by Officer")
    )

    conn.commit()
    conn.close()

    return redirect('/officer_dashboard')


@app.route('/reject/<int:app_id>')
def reject(app_id):
    if 'role' not in session or session['role'] != "officer":
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Update status
    cursor.execute(
        "UPDATE applications SET status='Rejected' WHERE id=?",
        (app_id,)
    )

    # Insert timeline log
    cursor.execute(
        "INSERT INTO application_logs (application_id, action) VALUES (?, ?)",
        (app_id, "Application Rejected by Officer")
    )

    conn.commit()
    conn.close()

    return redirect('/officer_dashboard')
# ---------------- START REVIEW ----------------
@app.route('/review/<int:app_id>')
def review(app_id):
    if 'role' not in session or session['role'] != "officer":
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Update status
    cursor.execute(
        "UPDATE applications SET status='Under Review' WHERE id=?",
        (app_id,)
    )

    # Insert timeline log
    cursor.execute(
        "INSERT INTO application_logs (application_id, action) VALUES (?, ?)",
        (app_id, "Application Under Review by Officer")
    )

    conn.commit()
    conn.close()

    return redirect('/officer_dashboard')
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)