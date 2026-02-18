from telebot import types
from datetime import datetime, timedelta
from handlers.start import show_main_menu
from core.database import save_booking
from core.database import get_user_bookings, delete_booking
from core.database import get_booked_times
from core.database import get_connection, confirm_booking  # Добавляем новые импорты

SERVICES = [
    {"name": "Маникюр", "duration": 60},
    {"name": "Педикюр", "duration": 90},
    {"name": "Стрижка", "duration": 45}
]

user_states = {}

def register_booking(bot):
    
    # ============= НОВЫЕ ОБРАБОТЧИКИ (с правильными отступами) =============
    
    # Обработчик подтверждения записи
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
    def confirm_booking_handler(call):
        booking_id = int(call.data.split("_")[1])
        
        if confirm_booking(booking_id):
            bot.answer_callback_query(call.id, "✅ Запись подтверждена! Спасибо!")
            bot.edit_message_text(
                "✅ *Запись подтверждена!*\n\nСпасибо, что подтвердили визит. Ждём вас! ✨",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Уведомление админа о подтверждении
            from config import ADMINS
            for admin_id in ADMINS:
                try:
                    bot.send_message(
                        admin_id,
                        f"✅ *Клиент подтвердил запись!*\n\n"
                        f"Запись #{booking_id} подтверждена клиентом.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка подтверждения", show_alert=True)

    # Обновленный обработчик отмены
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
    def cancel_booking_handler(call):
        booking_id = int(call.data.split("_")[1])
        
        # Получаем информацию о записи перед удалением
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, service, date, time FROM bookings WHERE id = ?", (booking_id,))
        booking = cursor.fetchone()
        conn.close()
        
        if delete_booking(booking_id):
            bot.answer_callback_query(call.id, "❌ Запись отменена")
            bot.edit_message_text(
                f"❌ *Запись отменена*\n\n"
                f"Услуга: {booking[1] if booking else 'Неизвестно'}\n"
                f"Дата: {booking[2] if booking else 'Неизвестно'}\n"
                f"Время: {booking[3] if booking else 'Неизвестно'}",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Уведомление админа об отмене
            from config import ADMINS
            for admin_id in ADMINS:
                try:
                    bot.send_message(
                        admin_id,
                        f"❌ *Клиент отменил запись!*\n\n"
                        f"Клиент: {booking[0] if booking else 'Неизвестно'}\n"
                        f"Услуга: {booking[1] if booking else 'Неизвестно'}\n"
                        f"Дата: {booking[2] if booking else 'Неизвестно'}\n"
                        f"Время: {booking[3] if booking else 'Неизвестно'}",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка отмены", show_alert=True)

    # ============= СТАРЫЕ ОБРАБОТЧИКИ =============
    
    # Просмотр записей
    @bot.message_handler(func=lambda message: message.text == "📋 Мои брони")
    def my_bookings(message):
        bookings = get_user_bookings(message.chat.id)

        if not bookings:
            bot.send_message(
                message.chat.id,
                "📋 *У вас пока нет активных записей*\n\n"
                "Хотите записаться? Нажмите кнопку «Записаться на услугу» в главном меню 👇\n\n"
                "Мы предлагаем:\n"
                "💅 Маникюр\n"
                "🦶 Педикюр\n"
                "✂️ Стрижку\n\n"
                "Ждем вас в нашем салоне! ✨",
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
                f"💅 *{service}*\n📅 {date}\n🕒 {time}\n"
                f"📊 Статус: {status_text}\n\n"
                f"_Будем ждать вас!_",
                parse_mode="Markdown",
                reply_markup=markup
            )

    # Перенос (удаление + запуск заново)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("reschedule_"))
    def reschedule_booking(call):
        booking_id = int(call.data.split("_")[1])
        delete_booking(booking_id)
        bot.answer_callback_query(call.id, "Выберите новую дату")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "🔁 Давайте выберем новую запись.")
        
        # Запускаем процесс заново
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for service in SERVICES:
            markup.add(service["name"])
        markup.add("⬅️ Назад")

        bot.send_message(call.message.chat.id, "Выберите услугу:", reply_markup=markup)
        user_states[call.message.chat.id] = {"step": "service"}

    # Назад
    @bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
    def go_back(message):
        if message.chat.id in user_states:
            del user_states[message.chat.id]
        show_main_menu(bot, message.chat.id)

    # Запуск записи
    @bot.message_handler(func=lambda message: message.text == "📅 Записаться на услугу")
    def start_booking(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for service in SERVICES:
            markup.add(service["name"])
        markup.add("⬅️ Назад")
        bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=markup)
        user_states[message.chat.id] = {"step": "service"}

    # Универсальный обработчик шагов
    @bot.message_handler(func=lambda message: message.chat.id in user_states)
    def process_steps(message):
        chat_id = message.chat.id
        state = user_states[chat_id]

        # Шаг 1 — Услуга
        if state["step"] == "service":
            if message.text not in [s["name"] for s in SERVICES]:
                bot.send_message(chat_id, "Пожалуйста, выберите услугу кнопкой.")
                return

            state["service"] = message.text
            state["step"] = "date"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            today = datetime.now()
            for i in range(3):
                day = today + timedelta(days=i)
                markup.add(day.strftime("%d.%m.%Y"))
            markup.add("⬅️ Назад")
            bot.send_message(chat_id, "Выберите дату:", reply_markup=markup)

        # Шаг 2 — Дата
        elif state["step"] == "date":
            selected_date = message.text
            state["date"] = selected_date
            state["step"] = "time"

            booked_times = get_booked_times(selected_date)
            all_times = ["10:00", "12:00", "14:00", "16:00"]
            free_times = [t for t in all_times if t not in booked_times]

            if not free_times:
                bot.send_message(chat_id, "❌ На эту дату нет свободного времени. Выберите другую дату.")
                state["step"] = "date"
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                today = datetime.now()
                for i in range(3):
                    day = today + timedelta(days=i)
                    markup.add(day.strftime("%d.%m.%Y"))
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "Выберите другую дату:", reply_markup=markup)
                return

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for i in range(0, len(free_times), 2):
                if i+1 < len(free_times):
                    markup.add(free_times[i], free_times[i+1])
                else:
                    markup.add(free_times[i])
            markup.add("⬅️ Назад")
            bot.send_message(chat_id, "Выберите время:", reply_markup=markup)

        # Шаг 3 — Время
        elif state["step"] == "time":
            state["time"] = message.text
            state["step"] = "name"
            bot.send_message(chat_id, "Введите ваше имя:")

        # Шаг 4 — Имя
        elif state["step"] == "name":
            state["name"] = message.text
            state["step"] = "phone"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton("📱 Поделиться номером", request_contact=True)
            markup.add(button)
            markup.add("⬅️ Назад")
            bot.send_message(
                chat_id,
                "Нажмите кнопку ниже, чтобы поделиться номером телефона:",
                reply_markup=markup
            )

    # Шаг 5 — Получение контакта
    @bot.message_handler(content_types=['contact'])
    def save_final_booking(message):
        chat_id = message.chat.id

        if chat_id not in user_states:
            return

        state = user_states[chat_id]
        state["phone"] = message.contact.phone_number

        # Проверяем, свободно ли время перед сохранением
        booked_times = get_booked_times(state["date"])
        
        if state["time"] in booked_times:
            bot.send_message(
                chat_id,
                "❌ К сожалению, это время только что заняли.\nПожалуйста, выберите другое."
            )
            state["step"] = "time"
            all_times = ["10:00", "12:00", "14:00", "16:00"]
            free_times = [t for t in all_times if t not in get_booked_times(state["date"])]
            
            if free_times:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for i in range(0, len(free_times), 2):
                    if i+1 < len(free_times):
                        markup.add(free_times[i], free_times[i+1])
                    else:
                        markup.add(free_times[i])
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "Выберите другое время:", reply_markup=markup)
            else:
                state["step"] = "date"
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                today = datetime.now()
                for i in range(3):
                    day = today + timedelta(days=i)
                    markup.add(day.strftime("%d.%m.%Y"))
                markup.add("⬅️ Назад")
                bot.send_message(chat_id, "На эту дату нет свободного времени. Выберите другую дату:", reply_markup=markup)
            return

        # Сохраняем запись
        success = save_booking(
            telegram_id=chat_id,
            service=state["service"],
            date=state["date"],
            time=state["time"],
            name=state["name"],
            phone=state["phone"]
        )

        if success:
            # Создаём кнопку "Главное меню"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🏠 Главное меню")

            bot.send_message(
                chat_id,
                f"✅ *Ваша запись создана!*\n\n"
                f"💅 *Услуга:* {state['service']}\n"
                f"📅 *Дата:* {state['date']}\n"
                f"🕒 *Время:* {state['time']}\n"
                f"🙋 *Имя:* {state['name']}\n"
                f"📱 *Телефон:* {state['phone']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"ℹ️ *Все ваши записи* находятся в разделе «Мои брони».\n"
                f"Там вы можете:\n"
                f"• 👀 Просмотреть все записи\n"
                f"• ❌ Отменить запись\n"
                f"• 🔁 Перенести на другое время\n\n"
                f"Статус вашей записи: *⏳ Ожидает подтверждения*\n"
                f"Мы напомним вам за 24 часа и за 1 час до визита!\n\n"
                f"Нажмите «🏠 Главное меню», чтобы вернуться",
                parse_mode="Markdown",
                reply_markup=markup
            )

            del user_states[chat_id]
            
        else:
            bot.send_message(
                chat_id,
                "❌ Произошла ошибка при сохранении записи. Пожалуйста, попробуйте позже."
            )
    
    # Обработчик кнопки "Главное меню"
    @bot.message_handler(func=lambda message: message.text == "🏠 Главное меню")
    def back_to_main_menu(message):
        show_main_menu(bot, message.chat.id)