import sqlite3

DB_NAME = "beauty_bot.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        name TEXT,
        phone TEXT,
        service TEXT,
        price INTEGER DEFAULT 0,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'pending',
        confirmed_at TIMESTAMP,
        reminder_24h_sent BOOLEAN DEFAULT 0,
        reminder_1h_sent BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    # Добавляем колонки если таблица уже существовала
    cursor.execute("PRAGMA table_info(bookings)")
    columns = [col[1] for col in cursor.fetchall()]
    migrations = [
        ('status',            "ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'pending'"),
        ('price',             "ALTER TABLE bookings ADD COLUMN price INTEGER DEFAULT 0"),
        ('confirmed_at',      "ALTER TABLE bookings ADD COLUMN confirmed_at TIMESTAMP"),
        ('reminder_24h_sent', "ALTER TABLE bookings ADD COLUMN reminder_24h_sent BOOLEAN DEFAULT 0"),
        ('reminder_1h_sent',  "ALTER TABLE bookings ADD COLUMN reminder_1h_sent BOOLEAN DEFAULT 0"),
    ]
    for col_name, sql in migrations:
        if col_name not in columns:
            cursor.execute(sql)

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


def get_user_bookings(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, service, date, time, status
        FROM bookings
        WHERE telegram_id = ? AND status != 'cancelled'
        ORDER BY date, time
    """, (telegram_id,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings


def get_booked_times(date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time FROM bookings
        WHERE date = ? AND status != 'cancelled'
    """, (date,))
    times = cursor.fetchall()
    conn.close()
    return [t[0] for t in times]


def delete_booking(booking_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()


def get_all_bookings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, telegram_id, name, phone, service, price, date, time, status, created_at
        FROM bookings
        ORDER BY date DESC, time DESC
    """)
    bookings = cursor.fetchall()
    conn.close()
    return bookings


def get_service_price(service_name):
    prices = {
        "Стрижка мужская":    800,
        "Стрижка женская":    1500,
        "Химическая завивка": 3500,
        "Уход за волосами":   2000,
        "Окрашивание":        4500,
        "Стрижка":            1200,
    }
    return prices.get(service_name, 0)


def save_booking(telegram_id, service, date, time, name, phone):
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем занято ли время
    cursor.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE date = ? AND time = ? AND status != 'cancelled'
    """, (date, time))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False

    price = get_service_price(service)

    # Сохраняем со статусом 'pending' — ждём подтверждения от клиента
    cursor.execute("""
        INSERT INTO bookings
            (telegram_id, name, phone, service, price, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (telegram_id, name, phone, service, price, date, time))

    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    print(f"✅ Запись #{booking_id} сохранена: {service} {date} {time} ({name})")
    return True


def confirm_booking(booking_id):
    """Клиент подтвердил визит через кнопку в напоминании"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bookings
        SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending'
    """, (booking_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if success:
        print(f"✅ Запись #{booking_id} подтверждена клиентом")
    return success


def mark_reminder_sent(booking_id, hours_before=24):
    """Атомарно отмечаем напоминание как отправленное — защита от дублей"""
    conn = get_connection()
    cursor = conn.cursor()
    if hours_before == 24:
        cursor.execute("""
            UPDATE bookings SET reminder_24h_sent = 1
            WHERE id = ? AND reminder_24h_sent = 0
        """, (booking_id,))
    else:
        cursor.execute("""
            UPDATE bookings SET reminder_1h_sent = 1
            WHERE id = ? AND reminder_1h_sent = 0
        """, (booking_id,))
    conn.commit()
    conn.close()