from telebot import types

def register_start(bot):
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        show_main_menu(bot, message.chat.id)

def show_main_menu(bot, chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Все кнопки главного меню
    btn1 = types.KeyboardButton("📅 Записаться на услугу")
    btn2 = types.KeyboardButton("💅 Услуги и цены")
    btn3 = types.KeyboardButton("❓ Часто задаваемые вопросы")
    btn4 = types.KeyboardButton("📍 Адрес и контакты")
    btn5 = types.KeyboardButton("📩 Связаться с админом")
    btn6 = types.KeyboardButton("📋 Мои брони")
    
    # Располагаем кнопки в 2 столбца
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    welcome_text = (
        "🌸 *Добро пожаловать в салон красоты!*\n\n"
        "Мы рады видеть вас! С помощью этого бота вы можете:\n"
        "• ✨ Записаться на услугу\n"
        "• 💅 Посмотреть услуги и цены\n"
        "• ❓ Получить ответы на вопросы\n"
        "• 📍 Узнать наш адрес\n"
        "• 📩 Связаться с администратором\n\n"
        "Выберите нужный пункт в меню 👇"
    )
    
    bot.send_message(
        chat_id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=markup
    )