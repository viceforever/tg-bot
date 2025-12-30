import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import Conflict
from config import config
from database.db_manager import DatabaseManager
from telegram_collector.collector import MessageCollector
from telegram_admin.admin_bot import AdminBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramCollectorBot:
    """Главный класс бота, объединяющий все модули"""
    
    def __init__(self):
        """Инициализация бота"""
        self.db_manager = DatabaseManager()
        self.collector = MessageCollector(self.db_manager)
        self.admin_bot = AdminBot(self.db_manager)
        self.application = None
    
    def setup_application(self):
        """Настройка приложения"""
        # Проверяем конфигурацию
        if not config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле")
        if not config.ADMIN_ID or config.ADMIN_ID == 0:
            raise ValueError("ADMIN_ID не установлен в .env файле")
        
        # Создаем таблицы в БД
        try:
            self.db_manager.create_tables()
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации БД: {e}")
            logger.error("Убедитесь, что PostgreSQL запущен и база данных создана")
            raise
        
        # Создаем приложение Telegram
        self.application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики команд администратора
        for handler in self.admin_bot.get_handlers():
            self.application.add_handler(handler)
        
        # Добавляем обработчик отредактированных сообщений ПЕРВЫМ (более высокий приоритет)
        async def edited_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.edited_message:
                await self.collector.handle_edited_message(update, context)
                return  # останавливаем обработку, чтобы не обработать дважды
        
        # Добавляем обработчик с более высоким приоритетом (группа 0)
        self.application.add_handler(
            MessageHandler(filters.ALL, edited_message_handler),
            group=0
        )
        
        # Добавляем обработчик всех сообщений для сбора данных (группа 1)
        # Обрабатываем только обычные сообщения (не команды и не отредактированные)
        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Пропускаем отредактированные сообщения (они обработаны в группе 0)
            if update.edited_message:
                return
            if update.message:
                await self.collector.handle_message(update, context)
        
        self.application.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, message_handler),
            group=1
        )
        
        # Добавляем обработчик реакций на сообщения
        from telegram.ext import BaseHandler
        
        class MessageReactionHandler(BaseHandler):
            """Обработчик для обновлений о реакциях на сообщения"""
            def __init__(self, callback):
                super().__init__(callback)
            
            def check_update(self, update):
                # Проверяем наличие message_reaction в обновлении
                return hasattr(update, 'message_reaction') and update.message_reaction is not None
        
        async def message_reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await self.collector.handle_message_reaction(update, context)
        
        # Добавляем обработчик для реакций с высоким приоритетом
        self.application.add_handler(
            MessageReactionHandler(message_reaction_handler),
            group=2
        )
        
        
        logger.info("Бот инициализирован")


def main():
    """Главная функция"""
    bot = TelegramCollectorBot()
    
    try:
        # Настраиваем приложение
        bot.setup_application()
        
        logger.info("Запуск бота...")
        logger.info("Бот успешно запущен. Нажмите Ctrl+C для остановки.")
        
        # Добавляем обработчик ошибок Conflict
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик ошибок"""
            if isinstance(context.error, Conflict):
                logger.warning("Обнаружен конфликт: другой экземпляр бота уже запущен. "
                             "Остановите другие экземпляры и перезапустите бота.")
            else:
                logger.error(f"Необработанное исключение: {context.error}", exc_info=context.error)
        
        bot.application.add_error_handler(error_handler)
        
        # Запускаем бота (блокирующий вызов)
        # allowed_updates включает все типы обновлений для сбора сообщений
        bot.application.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "channel_post", "edited_message", "message_reaction"]
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Conflict as e:
        logger.error(f"Конфликт: другой экземпляр бота уже запущен. {e}")
        logger.error("Остановите все другие экземпляры бота и попробуйте снова.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()

