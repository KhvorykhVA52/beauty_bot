import time
import threading
from datetime import datetime
from core.database import (
    get_pending_bookings_for_reminder, 
    mark_reminder_sent,
    confirm_booking
)
from telebot import types

class ReminderService:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        
    def start(self):
        """Запуск сервиса напоминаний в отдельном потоке"""
        thread = threading.Thread(target=self._run)
        thread.daemon = True
        thread.start()
        print("✅ Сервис напоминаний запущен")
    
    def _run(self):
        """Основной цикл проверки напоминаний"""
        while self.running:
            try:
                # Проверка напоминаний за 24 часа
                self._check_reminders(24)
                
                # Проверка напоминаний за 1 час
                self._check_reminders(1)
                
                # Проверка каждые 60 секунд
                time.sleep(60)
                
            except Exception as e:
                print(f"❌ Ошибка в сервисе напоминаний: {e}")
                time.sleep(60)
    
    def _check_reminders(self, hours_before):
        """Проверка и отправка напоминаний"""
        bookings = get_pending_bookings_for_reminder(hours_before)
        
        for booking in bookings:
            booking_id, telegram_id, service, date, time, name = booking
            
            if hours_before == 24:
                self._send_24h_reminder(telegram_id, booking_id, service, date, time, name)
            else:
                self._send_1h_reminder(telegram_id, booking_id, service, date, time, name)
    
    def _send_24h_reminder(self, chat_id, booking_id, service, date, time, name):
        """Отправка напоминания за 24 часа"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтверждаю", callback_data=f"confirm_{booking_id}"),
            types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{booking_id}")
        )
        
        text = (
            f"👋 *Здравствуйте, {name}!*\n\n"
            f"⏰ *Напоминание о записи*\n"
            f"Через 24 часа, {date} в {time}, у вас запланирована услуга:\n"
            f"💅 *{service}*\n\n"
            f"Пожалуйста, подтвердите, что вы придёте:\n"
            f"✅ *Подтверждаю* — я буду точно\n"
            f"❌ *Отменить* — не смогу прийти"
        )
        
        try:
            self.bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )
            mark_reminder_sent(booking_id, 24)
            print(f"✅ Напоминание за 24ч отправлено (запись #{booking_id})")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания #{booking_id}: {e}")
    
    def _send_1h_reminder(self, chat_id, booking_id, service, date, time, name):
        """Отправка напоминания за 1 час"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, я в пути", callback_data=f"confirm_{booking_id}"),
            types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{booking_id}")
        )
        
        text = (
            f"🚗 *{name}, вы уже в пути?*\n\n"
            f"⏰ Через 1 час, в {time}, у вас запланирована услуга:\n"
            f"💅 *{service}*\n\n"
            f"Подтвердите, пожалуйста, что вы идёте:\n"
            f"✅ *Да, я в пути*\n"
            f"❌ *Отменить* — не смогу прийти"
        )
        
        try:
            self.bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )
            mark_reminder_sent(booking_id, 1)
            print(f"✅ Напоминание за 1ч отправлено (запись #{booking_id})")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания #{booking_id}: {e}")