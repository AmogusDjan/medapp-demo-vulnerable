import sqlite3

conn = sqlite3.connect('medapp.db')
c = conn.cursor()

# Пациенты
c.execute('''
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    phone TEXT,
    email TEXT,
    policy TEXT
)
''')

# Врачи
c.execute('''
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    specialty TEXT NOT NULL
)
''')

# Записи на приём (с историей болезней)
c.execute('''
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    diagnosis TEXT,
    prescription TEXT
)
''')

# Тестовые пациенты (пароли в открытом виде — тоже учебная "уязвимость")
c.executemany('INSERT OR IGNORE INTO patients (username, password, full_name, phone, email, policy) VALUES (?,?,?,?,?,?)', [
    ('ivanov',  'pass123', 'Иванов Иван Иванович',  '+7-900-111-11-11', 'ivanov@mail.ru',  '1234 5678 9012'),
    ('petrova', 'qwerty',  'Петрова Анна Сергеевна', '+7-900-222-22-22', 'petrova@mail.ru', '9876 5432 1098'),
])

# Тестовые врачи
c.executemany('INSERT OR IGNORE INTO doctors (full_name, specialty) VALUES (?,?)', [
    ('Смирнов Алексей Петрович', 'Терапевт'),
    ('Кузнецова Ольга Ивановна', 'Кардиолог'),
    ('Соколов Дмитрий Андреевич', 'Невролог'),
])

# Тестовые записи (для демонстрации IDOR — у второго пациента есть запись, которую видит первый)
c.executemany('INSERT OR IGNORE INTO appointments (id, patient_id, doctor_id, date, diagnosis, prescription) VALUES (?,?,?,?,?,?)', [
    (100, 1, 1, '2025-01-15', 'ОРВИ', 'Постельный режим, обильное питьё'),
    (101, 1, 2, '2025-02-10', 'Гипертония', 'Эналаприл 10мг'),
    (102, 2, 3, '2025-03-05', 'Мигрень', 'Суматриптан по требованию'),
    (103, 2, 1, '2025-03-20', 'Ангина', 'Амоксициллин 500мг 7 дней'),
])

conn.commit()
conn.close()
print("База данных создана: medapp.db")