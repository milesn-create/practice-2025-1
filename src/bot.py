import logging
import sqlite3
from datetime import datetime
from dateutil import parser
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)

logger = logging.getLogger(__name__)

# Состояния разговора
WAITING_NAME = 1
WAITING_BIRTHDAY = 2

# Токен вашего бота
BOT_TOKEN = "7516274502:AAEraGsLf7MZ0_KvsqcAG65uoYVP3bchu7k"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS birthdays
        (user_id INTEGER, person_name TEXT, birthday DATE)
    ''')
    conn.commit()
    conn.close()

# Команда /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет! Я бот для напоминаний о днях рождения. 👋\n"
        "Используйте команду /add чтобы добавить день рождения.\n"
        "Используйте команду /list чтобы увидеть все сохраненные дни рождения."
    )

# Начало добавления дня рождения
def add_birthday(update: Update, context: CallbackContext):
    update.message.reply_text("Пожалуйста, введите имя человека:")
    return WAITING_NAME

# Обработка имени
def process_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    update.message.reply_text(
        "Теперь введите дату рождения в формате ДД.ММ.ГГГГ:"
    )
    return WAITING_BIRTHDAY

# Обработка даты рождения
def process_birthday(update: Update, context: CallbackContext):
    try:
        birthday = parser.parse(update.message.text, dayfirst=True)
        name = context.user_data['name']
        
        conn = sqlite3.connect('birthdays.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO birthdays (user_id, person_name, birthday) VALUES (?, ?, ?)",
            (update.effective_user.id, name, birthday.strftime('%Y-%m-%d'))
        )
        conn.commit()
        conn.close()

        update.message.reply_text(
            f"Отлично! Я сохранил день рождения {name} - {birthday.strftime('%d.%m.%Y')}. "
            f"Я напомню вам об этом в день рождения в 9:00 утра! 🎉"
        )
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text(
            "Извините, я не смог распознать дату. Пожалуйста, используйте формат ДД.ММ.ГГГГ:"
        )
        return WAITING_BIRTHDAY

# Отмена операции
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Список всех дней рождения
def list_birthdays(update: Update, context: CallbackContext):
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute(
        "SELECT person_name, birthday FROM birthdays WHERE user_id = ?",
        (update.effective_user.id,)
    )
    birthdays = c.fetchall()
    conn.close()

    if not birthdays:
        update.message.reply_text("У вас пока нет сохраненных дней рождения.")
        return

    message = "Сохраненные дни рождения:\n\n"
    for name, birthday in birthdays:
        birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
        message += f"🎂 {name}: {birthday_date.strftime('%d.%m.%Y')}\n"
    
    update.message.reply_text(message)

# Проверка и отправка напоминаний
def check_birthdays(context: CallbackContext):
    try:
        conn = sqlite3.connect('birthdays.db')
        c = conn.cursor()
        today = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%m-%d')
        
        c.execute(
            "SELECT user_id, person_name, birthday FROM birthdays"
        )
        birthdays = c.fetchall()
        conn.close()

        for user_id, name, birthday in birthdays:
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
            if birthday_date.strftime('%m-%d') == today:
                age = datetime.now().year - birthday_date.year
                context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 Сегодня день рождения у {name}! "
                         f"Ему/ей исполняется {age} лет! "
                         f"Не забудьте поздравить! 🎂"
                )
    except Exception as e:
        logger.error(f"Ошибка при проверке дней рождения: {e}")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Произошла ошибка: {context.error}")
    if update:
        update.message.reply_text("Извините, произошла ошибка. Попробуйте еще раз.")

def main():
    try:
        # Инициализация базы данных
        init_db()

        # Создание updater и dispatcher
        updater = Updater(BOT_TOKEN)
        dp = updater.dispatcher

        # Установка команд в меню бота
        commands = [
            ('start', 'Запустить бота'),
            ('add', 'Добавить день рождения'),
            ('list', 'Показать все дни рождения'),
            ('cancel', 'Отменить текущее действие')
        ]
        updater.bot.set_my_commands(commands)

        # Добавление обработчиков команд
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add', add_birthday)],
            states={
                WAITING_NAME: [MessageHandler(Filters.text & ~Filters.command, process_name)],
                WAITING_BIRTHDAY: [MessageHandler(Filters.text & ~Filters.command, process_birthday)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("list", list_birthdays))
        dp.add_handler(conv_handler)
        dp.add_error_handler(error_handler)

        # Настройка планировщика для проверки дней рождения
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Moscow'))
        scheduler.add_job(
            check_birthdays,
            'cron',
            hour=9,
            minute=0,
            args=[updater.dispatcher]
        )
        scheduler.start()

        # Запуск бота
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == '__main__':
    main() 