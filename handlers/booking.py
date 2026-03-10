from telebot import types
from datetime import datetime, timedelta
from handlers.start import show_main_menu
from core.database import save_booking
from core.database import get_user_bookings, delete_booking
from core.database import get_booked_times
from core.database import get_connection, confirm_booking

# ============= УСЛУГИ ПАРИКМАХЕРА =============
SERVICES = [
    {"name": "Стрижка мужская",    "duration": 45,  "emoji": "✂️"},
    {"name": "Стрижка женская",    "duration": 60,  "emoji": "✂️"},
    {"name": "Химическая завивка", "duration": 120, "emoji": "🌀"},
    {"name": "Уход за волосами",   "duration": 60,  "emoji": "💆"},
    {"name": "Окрашивание",        "duration": 180, "emoji": "🎨"},
]

ALL_TIME_SLOTS = [
    f"{h:02d}:{m:02d}"
    for h in range(10, 20)
    for m in (0, 30)
    if not (h == 19 and m == 30)
]

def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} мин"
    elif minutes == 60:
        return "1 час"
    elif minutes == 90:
        return "1.5 часа"
    elif minutes == 120:
        return "2 часа"
    elif minutes == 180:
        return "3 часа"
    else:
        h, m = minutes // 60, minutes % 60
        return f"{h}ч {m}мин" if m else f"{h} ч"

def get_free_slots(date, duration_minutes):
    booked_times = get_booked_times(date)
    free = []
    for slot in ALL_TIME_SLOTS:
        slot_dt = datetime.strptime(slot, "%H:%M")
        end_dt = slot_dt + timedelta(minutes=duration_minutes)
        conflict = False
        check = slot_dt
        while check < end_dt:
            if check.strftime("%H:%M") in booked_times:
                conflict = True
                break
            check += timedelta(minutes=30)
        if not conflict and end_dt <= datetime.strptime("20:00", "%H:%M"):
            free.append(slot)
    return free

user_states = {}

def register_booking(bot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
    def confirm_booking_handler(call):
        booking_id = int(call.data.split("_")[1])
        if confirm_booking(booking_id):
            bot.answer_callback_query(call.id, "✅ Запись подтверждена! Спасибо!")
            bot.edit_message_text(
                "✅ *Запись подтверждена!*\n\nСпасибо, что подтвердили визит. Ждём вас! ✨",
                call.message.chat.id, call.message.message_id, parse_mode="Markdown"
            )
            from config import ADMINS
            for admin_id in ADMINS:
                try:
                    bot.send_message(admin_id, f"✅ *Клиент подтвердил запись #{booking_id}*", parse_mode="Markdown")
                except:
                    pass
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка подтверждения", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
    def cancel_booking_handler(call):
        try:
            booking_id = int(call.data.split("_")[1])
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, service, date, time FROM bookings WHERE id = ?", (booking_id,))
            booking = cursor.fetchone()
            if not booking:
                bot.answer_callback_query(call.id, "✅ Запись уже удалена")
                try:
                    bot.edit_message_text("❌ *Запись уже была удалена*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
                except:
                    pass
                conn.close()
                return
            cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "✅ Запись отменена")
            try:
                bot.edit_message_text(
                    f"❌ *Запись отменена*\n\n✂️ {booking[1]}\n📅 {booking[2]}\n🕒 {booking[3]}",
                    call.message.chat.id, call.message.message_id, parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Ошибка редактирования: {e}")
            from config import ADMINS
            for admin_id in ADMINS:
                try:
                    bot.send_message(
                        admin_id,
                        f"❌ *Клиент отменил запись!*\n\n👤 {booking[0]}\n✂️ {booking[1]}\n📅 {booking[2]}\n🕒 {booking[3]}",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        except Exception as e:
            print(f"Ошибка при отмене: {e}")
            bot.answer_callback_query(call.id, "❌ Произошла ошибка", show_alert=True)

    @bot.message_handler(func=lambda message: message.text == "📋 Мои брони")
    def my_bookings(message):
        bookings = get_user_bookings(message.chat.id)
        if not bookings:
            bot.send_message(
                message.chat.id,
                "📋 *У вас пока нет активных записей*\n\n"
                "Нажмите «📅 Записаться на услугу», чтобы выбрать удобное время ✨",
                parse_mode="Markdown"
            )
            return
        for booking in bookings:
            booking_id, service, date, time, status = booking
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{booking_id}"),
                types.InlineKeyboardButton("🔁 Перенести", callback_data=f"reschedule_{booking_id}")
            )
            status_text = "✅ Подтверждена" if status == "confirmed" else "⏳ Ожидает подтверждения"
            bot.send_message(
                message.chat.id,
                f"✂️ *{service}*\n📅 {date}\n🕒 {time}\n📊 {status_text}",
                parse_mode="Markdown", reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reschedule_"))
    def reschedule_booking(call):
        booking_id = int(call.data.split("_")[1])
        delete_booking(booking_id)
        bot.answer_callback_query(call.id, "Выберите новое время")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "🔁 Выберем новое время.")
        _show_services(bot, call.message.chat.id)

    @bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
    def go_back(message):
        chat_id = message.chat.id
        step = user_states.get(chat_id, {}).get("step")
        if step in ("date", "time", "name", "phone"):
            _show_services(bot, chat_id)
        else:
            user_states.pop(chat_id, None)
            show_main_menu(bot, chat_id)

    @bot.message_handler(func=lambda message: message.text == "📅 Записаться на услугу")
    def start_booking(message):
        _show_services(bot, message.chat.id)

    def _show_services(bot, chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for s in SERVICES:
            markup.add(f"{s['emoji']} {s['name']} ({format_duration(s['duration'])})")
        markup.add("⬅️ Назад")
        bot.send_message(chat_id, "✂️ Выберите услугу:", reply_markup=markup)
        user_states[chat_id] = {"step": "service"}

    @bot.message_handler(func=lambda message: message.chat.id in user_states)
    def process_steps(message):
        chat_id = message.chat.id
        state = user_states[chat_id]

        if state["step"] == "service":
            service_obj = None
            for s in SERVICES:
                if message.text == f"{s['emoji']} {s['name']} ({format_duration(s['duration'])})":
                    service_obj = s
                    break
            if not service_obj:
                bot.send_message(chat_id, "Пожалуйста, выберите услугу кнопкой.")
                return
            state["service"] = service_obj["name"]
            state["duration"] = service_obj["duration"]
            state["step"] = "date"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            today = datetime.now()
            for i in range(7):
                markup.add((today + timedelta(days=i)).strftime("%d.%m.%Y"))
            markup.add("⬅️ Назад")
            bot.send_message(chat_id, "📅 Выберите дату:", reply_markup=markup)

        elif state["step"] == "date":
            state["date"] = message.text
            state["step"] = "time"
            free_times = get_free_slots(message.text, state["duration"])
            if not free_times:
                bot.send_message(chat_id, "❌ На эту дату нет свободного времени. Выберите другую.")
                state["step"] = "date"
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                today = datetime.now()
                for i in range(7):
                    markup.add((today + timedelta(days=i)).strftime("%d.%m.%Y"))
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "Выберите другую дату:", reply_markup=markup)
                return
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for i in range(0, len(free_times), 3):
                markup.add(*free_times[i:i+3])
            markup.add("⬅️ Назад")
            bot.send_message(
                chat_id,
                f"🕒 Выберите время:\n_Длительность: {format_duration(state['duration'])}_",
                reply_markup=markup, parse_mode="Markdown"
            )

        elif state["step"] == "time":
            state["time"] = message.text
            state["step"] = "name"
            bot.send_message(chat_id, "👤 Введите ваше имя:")

        elif state["step"] == "name":
            state["name"] = message.text
            state["step"] = "phone"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("📱 Поделиться номером", request_contact=True))
            markup.add("⬅️ Назад")
            bot.send_message(chat_id, "📱 Поделитесь номером телефона:", reply_markup=markup)

    @bot.message_handler(content_types=['contact'])
    def save_final_booking(message):
        chat_id = message.chat.id
        if chat_id not in user_states:
            return
        state = user_states[chat_id]
        state["phone"] = message.contact.phone_number

        free_times = get_free_slots(state["date"], state["duration"])
        if state["time"] not in free_times:
            bot.send_message(chat_id, "❌ Это время только что заняли. Выберите другое.")
            state["step"] = "time"
            if free_times:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for i in range(0, len(free_times), 3):
                    markup.add(*free_times[i:i+3])
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "Выберите другое время:", reply_markup=markup)
            else:
                state["step"] = "date"
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                today = datetime.now()
                for i in range(7):
                    markup.add((today + timedelta(days=i)).strftime("%d.%m.%Y"))
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "На эту дату нет времени. Выберите другую:", reply_markup=markup)
            return

        success = save_booking(
            telegram_id=chat_id,
            service=state["service"],
            date=state["date"],
            time=state["time"],
            name=state["name"],
            phone=state["phone"]
        )

        if success:
            end_time = (datetime.strptime(state["time"], "%H:%M") + timedelta(minutes=state["duration"])).strftime("%H:%M")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🏠 Главное меню")
            bot.send_message(
                chat_id,
                f"✅ *Запись создана!*\n\n"
                f"✂️ *Услуга:* {state['service']}\n"
                f"📅 *Дата:* {state['date']}\n"
                f"🕒 *Время:* {state['time']} — {end_time}\n"
                f"👤 *Имя:* {state['name']}\n"
                f"📱 *Телефон:* {state['phone']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Напомним за 24 часа и за 1 час до визита.\n"
                f"Управлять записью можно в разделе «📋 Мои брони».",
                parse_mode="Markdown", reply_markup=markup
            )
            del user_states[chat_id]
        else:
            bot.send_message(chat_id, "❌ Ошибка при сохранении. Попробуйте ещё раз.")

    @bot.message_handler(func=lambda message: message.text == "🏠 Главное меню")
    def back_to_main_menu(message):
        show_main_menu(bot, message.chat.id)