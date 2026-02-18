import sqlite3
from datetime import datetime, timedelta

DB_NAME = "beauty_bot.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Создаем таблицу со всеми нужными колонками
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
    
    # Проверяем, есть ли все колонки (если таблица уже существовала)
    cursor.execute("PRAGMA table_info(bookings)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Добавляем недостающие колонки
    if 'status' not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'price' not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN price INTEGER DEFAULT 0")
    if 'confirmed_at' not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN confirmed_at TIMESTAMP")
    if 'reminder_24h_sent' not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN reminder_24h_sent BOOLEAN DEFAULT 0")
    if 'reminder_1h_sent' not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN reminder_1h_sent BOOLEAN DEFAULT 0")
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_user_bookings(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, service, date, time, status 
        FROM bookings 
        WHERE telegram_id = ?
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
    conn = sqlite3.connect('beauty_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, telegram_id, name, phone, service, price, date, time, status, created_at 
        FROM bookings 
        ORDER BY date DESC, time DESC
    ''')
    
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def get_service_price(service_name):
    """Получение цены услуги по названию"""
    prices = {
        "Маникюр": 1500,
        "Педикюр": 2000,
        "Стрижка": 1200,
        "Классический маникюр": 1500,
        "Аппаратный маникюр": 1700,
        "Комбинированный маникюр": 1800,
        "Классический педикюр": 2000,
        "Аппаратный педикюр": 2200,
        "Комбинированный педикюр": 2400,
        "Женская стрижка": 2000,
        "Мужская стрижка": 1500,
        "Детская стрижка": 1000,
        "Укладка": 1200,
        "Тонирование": 2500,
        "Полное окрашивание": 4000,
        "Мелирование": 3500,
        "СПА-уход для рук": 1000,
        "Парафинотерапия": 800,
        "Массаж головы": 500
    }
    return prices.get(service_name, 0)

def save_booking(telegram_id, service, date, time, name, phone):
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем, занято ли время
    cursor.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE date = ? AND time = ? AND status != 'cancelled'
    """, (date, time))

    if cursor.fetchone()[0] > 0:
        conn.close()
        return False

    # Получаем цену услуги
    price = get_service_price(service)

    # Если свободно — сохраняем со статусом 'pending'
    cursor.execute("""
        INSERT INTO bookings (telegram_id, name, phone, service, price, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, name, phone, service, price, date, time, 'pending'))

    conn.commit()
    
    # Получаем id только что вставленной записи
    booking_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ Запись сохранена: id={booking_id}, {service}, {date} {time}")
    return True

def confirm_booking(booking_id):
    """Подтверждение записи клиентом"""
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
        print(f"✅ Запись {booking_id} подтверждена")
    return success

def get_pending_bookings_for_reminder(hours_before=24):
    """Получение записей, которым нужно отправить напоминание"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if hours_before == 24:
        cursor.execute("""
            SELECT id, telegram_id, service, date, time, name 
            FROM bookings 
            WHERE date = date('now', '+1 day') 
            AND status = 'pending'
            AND reminder_24h_sent = 0
        """)
    else:  # 1 час
        cursor.execute("""
            SELECT id, telegram_id, service, date, time, name 
            FROM bookings 
            WHERE date = date('now') 
            AND time = time('now', '+1 hour')
            AND status = 'pending'
            AND reminder_1h_sent = 0
        """)
    
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def mark_reminder_sent(booking_id, hours_before=24):
    """Отметка, что напоминание отправлено"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if hours_before == 24:
        cursor.execute("UPDATE bookings SET reminder_24h_sent = 1 WHERE id = ?", (booking_id,))
    else:
        cursor.execute("UPDATE bookings SET reminder_1h_sent = 1 WHERE id = ?", (booking_id,))
    
    conn.commit()
    conn.close()