import telebot
import time
import threading
from config import BOT_TOKEN, ADMINS
from core.database import init_db
from services.reminder_service import ReminderService

print("=" * 50)
print("🚀 ЗАПУСК БОТА")
print("=" * 50)

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Импортируем хендлеры
from handlers import start
from handlers import booking
from handlers import admin
from handlers import info

# Регистрируем обработчики
print("📝 Регистрация обработчиков...")
start.register_start(bot)
booking.register_booking(bot)
admin.register_admin(bot)
info.register_info_handlers(bot)
print("✅ Обработчики зарегистрированы")

if __name__ == "__main__":
    # Информация о запуске
    print(f"\n📱 Bot token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    print(f"👤 Admin IDs: {ADMINS}")
    print(f"💾 База данных: beauty_bot.db")
    print("=" * 50)
    
    # Инициализация БД
    print("💾 Инициализация базы данных...")
    try:
        init_db()
        print("✅ База данных готова")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
    
    # Запуск сервиса напоминаний
    print("⏰ Запуск сервиса напоминаний...")
    try:
        reminder_service = ReminderService(bot)
        reminder_service.start()
        print("✅ Сервис напоминаний активен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервиса напоминаний: {e}")
    
    print("-" * 50)
    print("✅ Бот запущен и готов к работе!")
    print("📝 Отправьте команду /start в Telegram")
    print("-" * 50)
    
    # Простой запуск без сложных обработок ошибок
    while True:
        try:
            bot.polling(non_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)