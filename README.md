# Telegram Collector

Система для автоматического сбора корпоративных переписок в Telegram.

## Описание проекта

Проект представляет собой Telegram-бота, который:
- Автоматически собирает все сообщения из чатов, в которые добавлен
- Сохраняет текст сообщений, документы, изображения и реакции
- Предоставляет администраторам возможность экспорта данных за указанный период

## Требования

- Python 3.8+
- PostgreSQL
- Telegram Bot Token

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/viceforever/tg-bot.git
cd tg-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Установите PostgreSQL:
   - Для Windows: скачайте и установите по ссылке (https://www.postgresql.org/download/windows/)
   - Используйте pgAdmin для управления базой данных

4. Создайте базу данных в PostgreSQL:
   - Подключитесь к серверу PostgreSQL
   - Создайте базу данных с названием `telegram_collector` (или другое, как указано в `.env`)

5. Настройте файл `.env` (см. раздел "Конфигурация")

## Конфигурация

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Telegram Bot Token
# Получите токен у @BotFather в Telegram
TELEGRAM_BOT_TOKEN=ваш_токен_бота

# Admin Telegram ID
# Ваш Telegram ID (можно узнать через @userinfobot)
ADMIN_ID=ваш_telegram_id

# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_collector
DB_USER=postgres
DB_PASSWORD=ваш_пароль
```

### Описание полей .env файла:

- **TELEGRAM_BOT_TOKEN** - Токен вашего Telegram бота, полученный от @BotFather
- **ADMIN_ID** - Ваш Telegram ID (числовой идентификатор), можно узнать через бота @userinfobot
- **DB_HOST** - Адрес хоста базы данных PostgreSQL (обычно localhost)
- **DB_PORT** - Порт базы данных (по умолчанию 5432)
- **DB_NAME** - Имя базы данных, которую вы создали в PostgreSQL
- **DB_USER** - Имя пользователя PostgreSQL (обычно postgres)
- **DB_PASSWORD** - Пароль пользователя PostgreSQL

## Запуск

```bash
python main.py
```

## Использование

1. Добавьте бота в нужные чаты/группы
2. Выдайте минимальные права администратора боту для получения доступа к сообщениям
3. Используйте команды в личных сообщениях с ботом:

### Команды администратора:

- `/start` - Показать справку по командам
- `/chats` - Получить список всех чатов, из которых собираются сообщения
- `/export <chat_id> <days>` - Экспорт сообщений за последние N дней
  - Пример: `/export -5148403988 7` - экспорт за последние 7 дней
- `/export_date <chat_id> <start_date> <end_date>` - Экспорт за указанный период
  - Формат даты: YYYY-MM-DD
  - Пример: `/export_date -5148403988 2025-01-01 2025-01-31`

## Архитектура проекта

Проект имеет модульную архитектуру:

- **database/** - Модуль работы с базой данных
  - `models.py` - SQLAlchemy модели
  - `db_manager.py` - Менеджер для работы с БД
  
- **telegram_collector/** - Модуль сбора сообщений
  - `collector.py` - Обработка и сохранение сообщений из Telegram
  
- **telegram_admin/** - Модуль админ-интерфейса
  - `admin_bot.py` - Команды администратора для экспорта данных
  
- **main.py** - Главный модуль, соединяющий все компоненты
- **config.py** - Конфигурация приложения

## База данных

Проект использует PostgreSQL с SQLAlchemy ORM. Структура базы данных включает:

- **users** - Пользователи Telegram
- **chats** - Чаты и группы
- **messages** - Сообщения
- **reactions** - Реакции на сообщения
- **documents** - Документы и файлы, прикрепленные к сообщениям

