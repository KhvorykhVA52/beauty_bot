from telebot import types
from config import ADMINS
from core.database import get_all_bookings
import pandas as pd
import os
from datetime import datetime

def register_admin(bot):
    
    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        if message.from_user.id not in ADMINS:
            bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Экспорт в Excel", "📋 Просмотреть все записи")
        markup.add("⬅️ Назад в главное меню")

        bot.send_message(
            message.chat.id, 
            "👨‍💼 *Панель администратора*\n\nВыберите действие:", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: message.text == "📊 Экспорт в Excel")
    def export_excel(message):
        if message.from_user.id not in ADMINS:
            bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
            return

        # Отправляем сообщение о начале подготовки
        status_msg = bot.send_message(message.chat.id, "⏳ Подготавливаю файл Excel...")

        bookings = get_all_bookings()

        if not bookings:
            bot.edit_message_text("📭 База данных пуста. Нет записей для экспорта.", 
                                  status_msg.chat.id, status_msg.message_id)
            return

        # Преобразуем в DataFrame с новыми колонками
        df = pd.DataFrame(bookings, columns=[
            "ID", 
            "Telegram ID", 
            "Имя", 
            "Телефон", 
            "Услуга", 
            "Цена (₽)", 
            "Дата", 
            "Время", 
            "Статус", 
            "Дата создания"
        ])

        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"bookings_export_{timestamp}.xlsx"
        
        # Сохраняем в Excel
        df.to_excel(file_name, index=False)

        # Отправляем файл
        with open(file_name, "rb") as f:
            bot.send_document(
                message.chat.id, 
                f,
                caption=f"📊 Экспорт записей от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )

        # Удаляем временный файл
        os.remove(file_name)
        
        # Удаляем сообщение о подготовке
        bot.delete_message(status_msg.chat.id, status_msg.message_id)

    @bot.message_handler(func=lambda message: message.text == "📋 Просмотреть все записи")
    def view_all_bookings(message):
        if message.from_user.id not in ADMINS:
            bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
            return

        bookings = get_all_bookings()

        if not bookings:
            bot.send_message(message.chat.id, "📭 База данных пуста.")
            return

        # Отправляем статистику
        total = len(bookings)
        
        # Подсчет по статусам
        confirmed = sum(1 for b in bookings if b[8] == 'confirmed')
        pending = sum(1 for b in bookings if b[8] == 'pending')
        
        bot.send_message(
            message.chat.id,
            f"📊 *Статистика*\n\n"
            f"Всего записей: {total}\n"
            f"✅ Подтверждено: {confirmed}\n"
            f"⏳ Ожидают: {pending}\n\n"
            f"📋 *Последние 5 записей:*",
            parse_mode="Markdown"
        )

        # Показываем последние 5 записей
        for booking in bookings[-5:]:
            booking_id, telegram_id, name, phone, service, price, date, time, status, created_at = booking
            
            status_emoji = "✅" if status == "confirmed" else "⏳"
            status_text = "Подтверждена" if status == "confirmed" else "Ожидает"
            
            bot.send_message(
                message.chat.id,
                f"🆔 *ID:* {booking_id}\n"
                f"👤 *Клиент:* {name}\n"
                f"📱 *Телефон:* {phone}\n"
                f"💅 *Услуга:* {service}\n"
                f"💰 *Цена:* {price}₽\n"
                f"📅 *Дата:* {date}\n"
                f"🕒 *Время:* {time}\n"
                f"{status_emoji} *Статус:* {status_text}\n"
                f"📝 *Дата записи:* {created_at}\n"
                f"───────────────",
                parse_mode="Markdown"
            )

    @bot.message_handler(func=lambda message: message.text == "⬅️ Назад в главное меню")
    def back_to_main(message):
        from handlers.start import show_main_menu
        show_main_menu(bot, message.chat.id)