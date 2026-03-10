import threading
import time
from datetime import datetime, timedelta
from core.database import get_connection, mark_reminder_sent
from telebot import types


class ReminderService:
    def __init__(self, bot):
        self.bot = bot
        self.running = False

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        print("✅ Сервис напоминаний запущен")

    def stop(self):
        self.running = False

    def _run(self):
        while self.running:
            try:
                self._check_reminders()
            except Exception as e:
                print(f"❌ Критическая ошибка сервиса напоминаний: {e}")
            time.sleep(60)  # каждую минуту — не пропустим ни одно окно

    def _check_reminders(self):
        now = datetime.now()
        print(f"⏰ Проверка напоминаний: {now.strftime('%d.%m.%Y %H:%M')}")

        conn = get_connection()
        cursor = conn.cursor()
        # Берём все записи которые ещё не отменены
        cursor.execute("""
            SELECT id, telegram_id, service, date, time, name,
                   reminder_24h_sent, reminder_1h_sent
            FROM bookings
            WHERE status != 'cancelled'
        """)
        bookings = cursor.fetchall()
        conn.close()

        for booking in bookings:
            booking_id, telegram_id, service, date, time_str, name, sent_24h, sent_1h = booking

            try:
                booking_dt = datetime.strptime(f"{date} {time_str}", "%d.%m.%Y %H:%M")
            except ValueError:
                print(f"⚠️ Неверный формат даты у записи #{booking_id}: '{date} {time_str}'")
                continue

            # Пропускаем прошедшие записи
            if booking_dt < now:
                continue

            # Считаем сколько минут до визита
            minutes_left = (booking_dt - now).total_seconds() / 60

            # ── Напоминание за 24 часа ───────────────────────────────────
            # Широкое окно: 23ч 30мин — 24ч 30мин (60 минут ширина)
            # Проверка каждую минуту = 100% попадание в окно
            if not sent_24h and (23 * 60 + 30) <= minutes_left <= (24 * 60 + 30):
                self._send_24h(telegram_id, booking_id, service, date, time_str, name)

            # ── Напоминание за 1 час ─────────────────────────────────────
            # Широкое окно: 50 — 70 минут (20 минут ширина)
            elif not sent_1h and 50 <= minutes_left <= 70:
                self._send_1h(telegram_id, booking_id, service, date, time_str, name)

    # ─────────────────────────────────────────────────────────────────────
    def _send_24h(self, telegram_id, booking_id, service, date, time_str, name):
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Подтверждаю",      callback_data=f"confirm_{booking_id}"),
            types.InlineKeyboardButton("❌ Отменить запись",  callback_data=f"cancel_{booking_id}")
        )

        text = (
            f"🔔 *Напоминание о завтрашнем визите*\n\n"
            f"Привет, {name}!\n\n"
            f"✂️ *Услуга:* {service}\n"
            f"📅 *Дата:* {date}\n"
            f"🕒 *Время:* {time_str}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Пожалуйста, нажмите одну из кнопок ниже 👇\n\n"
            f"✅ *Подтверждаю* — буду, всё по плану\n"
            f"❌ *Отменить* — планы изменились"
        )

        try:
            self.bot.send_message(telegram_id, text, parse_mode="Markdown", reply_markup=markup)
            # Отмечаем ПОСЛЕ успешной отправки
            mark_reminder_sent(booking_id, hours_before=24)
            print(f"✅ [24ч] #{booking_id} → {telegram_id} ({name})")
        except Exception as e:
            # НЕ отмечаем как отправленное — попробуем снова через минуту
            print(f"❌ [24ч] Ошибка #{booking_id}: {e}")

    # ─────────────────────────────────────────────────────────────────────
    def _send_1h(self, telegram_id, booking_id, service, date, time_str, name):
        text = (
            f"⏰ *Через 1 час ваш визит!*\n\n"
            f"{name}, ждём вас совсем скоро:\n\n"
            f"✂️ *Услуга:* {service}\n"
            f"📅 *Дата:* {date}\n"
            f"🕒 *Время:* {time_str}\n\n"
            f"Будем рады вас видеть! ✨"
        )

        try:
            self.bot.send_message(telegram_id, text, parse_mode="Markdown")
            mark_reminder_sent(booking_id, hours_before=1)
            print(f"✅ [1ч] #{booking_id} → {telegram_id} ({name})")
        except Exception as e:
            print(f"❌ [1ч] Ошибка #{booking_id}: {e}")