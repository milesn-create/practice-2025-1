import sqlite3
import schedule
import time
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
conn = sqlite3.connect('birthdays.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS birthdays
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              date TEXT NOT NULL)''')
conn.commit()

class BirthdayBot:
    def __init__(self):
        self.waiting_for_name = {}
        self.waiting_for_date = {}
        logger.info('BirthdayBot initialized')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f'Start command from user {update.effective_user.id}')
        # Создаем клавиатуру
        keyboard = [
            ['/start'],
            ['/add', '/list'],
            ['/delete'],
            ['/cancel']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🌟 <b>Привет!</b>\n"
            "Я твой бот-напоминалка о днях рождения \n"
            "Моя задача — помогать тебе не забывать о важных людях и вовремя напоминать, кого стоит поздравить 🎂💌\n\n"
            "С моей помощью ты можешь:\n"
            "• 👤 Добавить день рождения — /add\n"
            "• 📋 Посмотреть список всех — /list\n"
            "• 🗑 Удалить, если нужно — /delete\n"
            "• ❌ Отменить действие — /cancel\n\t"
            "Я постараюсь быть максимально полезным и ненавязчивым 😌\n"
            "Просто начни — и я всё подскажу!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def add_birthday(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f'Add command from chat {update.effective_chat.id}')
        await update.message.reply_text('Введите имя человека:')
        self.waiting_for_name[update.effective_chat.id] = True

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        logger.info(f'Handling name input from chat {chat_id}')
        if chat_id in self.waiting_for_name:
            name = update.message.text
            self.waiting_for_name.pop(chat_id)
            self.waiting_for_date[chat_id] = name
            await update.message.reply_text(
                f'Введите дату его рождения в формате ДД.ММ.ГГГГ:',
                reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру при вводе имени
            )
        else:
            logger.warning(f'Unexpected message in handle_name from chat {chat_id}')
            await update.message.reply_text('Извините, я не понимаю эту команду. Используйте /start для получения списка доступных команд.')

    async def handle_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        logger.info(f'Handling date input from chat {chat_id}')
        if chat_id in self.waiting_for_date:
            date_str = update.message.text
            try:
                datetime.strptime(date_str, '%d.%m.%Y')
                name = self.waiting_for_date.pop(chat_id)
                c.execute('INSERT INTO birthdays (name, date) VALUES (?, ?)', (name, date_str))
                conn.commit()
                
                # Возвращаем клавиатуру после добавления дня рождения
                keyboard = [
                    ['/add', '/list'],
                    ['/delete']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    f'Добавлено: {name} ({date_str})',
                    reply_markup=reply_markup
                )
                logger.info(f'Successfully added birthday for {name}: {date_str}')
            except ValueError:
                logger.warning(f'Invalid date format from chat {chat_id}')
                await update.message.reply_text('Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ.')
        else:
            logger.warning(f'Unexpected message in handle_date from chat {chat_id}')
            await update.message.reply_text('Извините, я не понимаю эту команду. Используйте /start для получения списка доступных команд.')

    async def list_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f'List command from chat {update.effective_chat.id}')
        c.execute('SELECT name, date FROM birthdays ORDER BY date')
        birthdays = c.fetchall()
        if birthdays:
            response = 'Список дней рождения:\n'
            for name, date in birthdays:
                response += f'{name}: {date}\n'
        else:
            response = 'Список дней рождения пуст.'
        
        # Отправляем результат с клавиатурой
        keyboard = [
            ['/add', '/list'],
            ['/delete']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(response, reply_markup=reply_markup)

    async def delete_birthday(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f'Delete command from chat {update.effective_chat.id}')
        await update.message.reply_text('Введите имя человека, чей день рождения нужно удалить:')
        self.waiting_for_name[update.effective_chat.id] = 'delete'

    async def handle_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        logger.info(f'Handling delete input from chat {chat_id}')
        if chat_id in self.waiting_for_name and self.waiting_for_name[chat_id] == 'delete':
            name = update.message.text
            self.waiting_for_name.pop(chat_id)
            c.execute('SELECT id FROM birthdays WHERE name = ?', (name,))
            result = c.fetchone()
            if result:
                c.execute('DELETE FROM birthdays WHERE id = ?', (result[0],))
                conn.commit()
                await update.message.reply_text(f'День рождения {name} удален.')
                logger.info(f'Successfully deleted birthday for {name}')
            else:
                await update.message.reply_text(f'День рождения {name} не найден.')
                logger.warning(f'Failed to delete birthday for {name}')
        else:
            logger.warning(f'Unexpected message in handle_delete from chat {chat_id}')
            await update.message.reply_text('Извините, я не понимаю эту команду. Используйте /start для получения списка доступных команд.')

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        logger.info(f'Cancel command from chat {chat_id}')
        
        # Очищаем все состояния
        if chat_id in self.waiting_for_name:
            self.waiting_for_name.pop(chat_id)
        if chat_id in self.waiting_for_date:
            self.waiting_for_date.pop(chat_id)
        
        # Возвращаем клавиатуру
        keyboard = [
            ['/start'],
            ['/add', '/list'],
            ['/delete'],
            ['/cancel']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text('Действие отменено.', reply_markup=reply_markup)

    async def check_birthdays(self, context: ContextTypes.DEFAULT_TYPE):
        today = datetime.now().strftime('%d.%m')
        c.execute('SELECT name, date FROM birthdays')
        birthdays = c.fetchall()
        for name, date in birthdays:
            if date[:5] == today:  # Compare only day and month
                logger.info(f'Birthday reminder for {name} today')
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=f'🎉 Ура! Сегодня день рождения празднует {name}! 🎂'
                )

def main():
    bot = BirthdayBot()
    
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token from BotFather
    application = Application.builder().token('8018148613:AAGl7IcDoFd1AV0dCVlGd7fH20iUCgA8Mpc').build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', bot.start))
    application.add_handler(CommandHandler('add', bot.add_birthday))
    application.add_handler(CommandHandler('list', bot.list_birthdays))
    application.add_handler(CommandHandler('delete', bot.delete_birthday))
    application.add_handler(CommandHandler('cancel', bot.cancel))
    
    # Обработчик текстовых сообщений
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        logger.info(f'Handling text message from chat {chat_id}')
        
        # Проверяем, ожидаем ли мы имя
        if chat_id in bot.waiting_for_name:
            if bot.waiting_for_name[chat_id] == 'delete':
                await bot.handle_delete(update, context)
            else:
                await bot.handle_name(update, context)
            return
        
        # Проверяем, ожидаем ли мы дату
        if chat_id in bot.waiting_for_date:
            await bot.handle_date(update, context)
            return
        
        # Если не ожидаем ничего, проверяем команду
        if update.message.text.startswith('/'):
            await update.message.reply_text('Извините, эта команда не распознана. Используйте /start для получения списка доступных команд.')
            return
        
        # Если сообщение не команда и не ожидаемое имя/дата
        await update.message.reply_text('Извините, я не понимаю эту команду. Используйте /start для получения списка доступных команд.')
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Schedule birthday check at 9:00 AM
    schedule.every().day.at("09:00").do(bot.check_birthdays)
    
    # Start the bot
    print("Бот запущен. Для остановки нажмите Ctrl+C")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # Start schedule loop
    while True:
        schedule.run_pending()
        time.sleep(1)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
