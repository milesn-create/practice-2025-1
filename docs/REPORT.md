# Отчет по разработке Telegram-бота для напоминаний о днях рождения

## 1. Общая информация

### 1.1 Назначение проекта
**Birthday Reminder Bot** - бот для:
- Управления списком дней рождения
- Автоматических напоминаний
- Персонализированных уведомлений

### 1.2 Основные характеристики
| Параметр       | Значение                     |
|----------------|-----------------------------|
| Язык           | Python 3.10+                |
| База данных    | SQLite                      |
| Пользователи   | Мультипользовательский режим|
| Точность       | Учет времени UTC+3          |

## 2. Технологический стек

### 2.1 Используемые библиотеки
```python  
requirements.txt:
python-telegram-bot==20.7
python-dotenv==1.0.0
sqlite3==3.35+  # Встроенная в Python
```
### 2.2 Структура БД
-- birthdays.db
CREATE TABLE IF NOT EXISTS birthdays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date DATE NOT NULL,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL
);--

