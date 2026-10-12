from flask import Flask, request, render_template, redirect, url_for, session, g
import sqlite3
import os
import traceback

app = Flask(__name__)
app.secret_key = 'super_secret_key_12345'  # в учебных целях

DATABASE = 'medapp.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        policy = request.form['policy']
        db = get_db()
        try:
            db.execute(
                'INSERT INTO patients (username, password, full_name, phone, email, policy) VALUES (?,?,?,?,?,?)',
                (username, password, full_name, phone, email, policy)
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Пользователь уже существует"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM patients WHERE username=? AND password=?',
            (username, password)
        ).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute('SELECT * FROM patients WHERE id=?', (session['user_id'],)).fetchone()
    appointments = db.execute('''
        SELECT a.id, a.date, a.diagnosis, a.prescription, d.full_name as doctor_name, d.specialty
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.date DESC
    ''', (session['user_id'],)).fetchall()
    return render_template('dashboard.html', user=user, appointments=appointments)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        # ============================================================
        # УЯЗВИМОСТЬ №1: CSRF
        # Нет никакой проверки CSRF-токена. POST-запрос с любого сайта
        # изменит данные, если у жертвы есть активная сессия.
        # ============================================================
        phone = request.form['phone']
        email = request.form['email']
        db.execute('UPDATE patients SET phone=?, email=? WHERE id=?',
                   (phone, email, session['user_id']))
        db.commit()
        return redirect(url_for('profile'))
    user = db.execute('SELECT * FROM patients WHERE id=?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user)

@app.route('/doctors')
def doctors():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    search = request.args.get('q', '')

    # ============================================================
    # УЯЗВИМОСТЬ №3: Information Disclosure
    # Прямая конкатенация в SQL-запрос + вывод traceback
    # при ошибке. Злоумышленник может ввести кавычку и увидеть
    # весь SQL-запрос и структуру БД.
    # ============================================================
    try:
        query = "SELECT * FROM doctors WHERE full_name LIKE '%" + search + "%' OR specialty LIKE '%" + search + "%'"
        doctors_list = db.execute(query).fetchall()
    except Exception as e:
        # Показываем пользователю полный traceback (это и есть утечка)
        return "<pre>" + traceback.format_exc() + "</pre>", 500

    return render_template('doctors.html', doctors=doctors_list, search=search)

@app.route('/appointment/<int:appointment_id>')
def appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()

    # ============================================================
    # УЯЗВИМОСТЬ №2: IDOR / BOLA
    # Запись забирается по ID БЕЗ проверки, что она принадлежит
    # текущему пользователю. Меняя /appointment/100 на /appointment/102,
    # можно читать чужие диагнозы.
    # ============================================================
    appt = db.execute('''
        SELECT a.*, d.full_name as doctor_name, d.specialty,
               p.full_name as patient_name, p.policy, p.phone
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ?
    ''', (appointment_id,)).fetchone()

    if not appt:
        return "Запись не найдена", 404
    return render_template('appointment.html', appt=appt)

@app.route('/book', methods=['POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # ============================================================
    # Ещё одна точка для CSRF: запись к врачу тоже без токена.
    # ============================================================
    doctor_id = request.form['doctor_id']
    date = request.form['date']
    db = get_db()
    db.execute('INSERT INTO appointments (patient_id, doctor_id, date, diagnosis, prescription) VALUES (?,?,?,?,?)',
               (session['user_id'], doctor_id, date, '—', '—'))
    db.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)