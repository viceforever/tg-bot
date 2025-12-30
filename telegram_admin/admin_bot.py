"""
Модуль для реализации админ-интерфейса бота
"""
import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime, timedelta
from typing import List
from config import config
from database.db_manager import DatabaseManager
from database.models import Message, Chat


class AdminBot:
    """Класс для обработки команд администратора"""
    
    def __init__(self, db_manager: DatabaseManager):
        """Инициализация админ-бота"""
        self.db_manager = db_manager
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id == config.ADMIN_ID
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("У вас нет доступа к этому боту.")
            return
        
        welcome_text = """
🤖 Бот для сбора корпоративных переписок

Доступные команды:
/start - Показать это сообщение
/chats - Список всех чатов
/export <chat_id> <days> - Экспорт сообщений за последние N дней
/export_date <chat_id> <start_date> <end_date> - Экспорт за период (формат: YYYY-MM-DD)

Примеры:
/export -5148403988 1 - Экспорт за последний день
/export_date -5148403988 2025-01-01 2025-01-31 - Экспорт за период
        """
        await update.message.reply_text(welcome_text)
    
    async def chats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /chats - список всех чатов"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("У вас нет доступа к этой команде.")
            return
        
        try:
            chats = self.db_manager.get_chat_list()
            if not chats:
                await update.message.reply_text("Чаты не найдены.")
                return
            
            # Если один чат сохранен и как group и как supergroup, оставляем только supergroup
            filtered_chats = {}
            supergroups_by_name = {}  # Словарь для отслеживания supergroup по названию
            
            # Сначала собираем все supergroup
            for chat in chats:
                if chat.chat_type == 'supergroup':
                    chat_title = (chat.title or '').strip().lower()
                    if chat_title:
                        # Если уже есть supergroup с таким названием, берем более свежий
                        if chat_title not in supergroups_by_name or chat.created_at > supergroups_by_name[chat_title].created_at:
                            supergroups_by_name[chat_title] = chat
            
            # Теперь фильтруем чаты
            for chat in chats:
                # Пропускаем личные чаты
                if chat.chat_type == 'private':
                    continue
                
                chat_title = (chat.title or '').strip().lower()
                
                # Если это group и есть supergroup с таким же названием, пропускаем
                if chat.chat_type == 'group' and chat_title and chat_title in supergroups_by_name:
                    continue
                
                # Добавляем чат в список (используем ID как ключ)
                filtered_chats[chat.id] = chat
            
            if not filtered_chats:
                await update.message.reply_text("Группы и супергруппы не найдены.")
                return
            
            response = "📋 Список чатов:\n\n"
            for chat in sorted(filtered_chats.values(), key=lambda x: x.created_at):
                chat_info = f"ID: {chat.id}\n"
                chat_info += f"Название: {chat.title or 'Без названия'}\n"
                chat_info += f"Создан: {chat.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                chat_info += "─" * 20 + "\n"
                response += chat_info
            
            # Разбиваем на части, если сообщение слишком длинное
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
        
        except Exception as e:
            await update.message.reply_text(f"Ошибка при получении списка чатов: {e}")
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /export - экспорт за последние N дней"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("У вас нет доступа к этой команде.")
            return
        
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "Использование: /export <chat_id> <days>\n"
                    "Пример: /export 123456789 7"
                )
                return
            
            # Поддерживаем как положительный, так и отрицательный ID
            # Если пользователь ввел положительный ID для группы, пробуем оба варианта
            chat_id = int(args[0])
            days = int(args[1])
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Пробуем найти сообщения с указанным ID
            messages = self.db_manager.get_messages_by_date_range(chat_id, start_date, end_date)
            
            # Если не найдено и ID положительный, пробуем отрицательный (для групп)
            if not messages and chat_id > 0:
                messages = self.db_manager.get_messages_by_date_range(-chat_id, start_date, end_date)
                if messages:
                    chat_id = -chat_id  # Обновляем для сообщения об ошибке
            
            if not messages:
                await update.message.reply_text(
                    f"Сообщения не найдены в чате {chat_id} за последние {days} дней."
                )
                return
            
            # Формируем экспорт
            export_text = self._format_export(messages, start_date, end_date)
            
            # Отправляем файл, если сообщение слишком длинное
            if len(export_text) > 4000:
                # Сохраняем во временный файл
                filename = f"export_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(export_text)
                
                try:
                    with open(filename, 'rb') as file:
                        await update.message.reply_document(
                            document=file,
                            filename=filename
                        )
                finally:
                    # Удаляем временный файл
                    if os.path.exists(filename):
                        os.remove(filename)
            else:
                await update.message.reply_text(export_text)
        
        except ValueError:
            await update.message.reply_text("Ошибка: неверный формат аргументов.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при экспорте: {e}")
    
    async def export_date_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /export_date - экспорт за период"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("У вас нет доступа к этой команде.")
            return
        
        try:
            args = context.args
            if len(args) < 3:
                await update.message.reply_text(
                    "Использование: /export_date <chat_id> <start_date> <end_date>\n"
                    "Формат даты: YYYY-MM-DD\n"
                    "Пример: /export_date 123456789 2025-01-01 2025-01-31"
                )
                return
            
            # Поддерживаем как положительный, так и отрицательный ID
            chat_id = int(args[0])
            start_date = datetime.strptime(args[1], "%Y-%m-%d")
            end_date = datetime.strptime(args[2], "%Y-%m-%d")
            # Добавляем время начала и конца дня (в UTC)
            start_date = start_date.replace(hour=0, minute=0, second=0)
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
            # Пробуем найти сообщения с указанным ID
            messages = self.db_manager.get_messages_by_date_range(chat_id, start_date, end_date)
            
            # Если не найдено и ID положительный, пробуем отрицательный (для групп)
            if not messages and chat_id > 0:
                messages = self.db_manager.get_messages_by_date_range(-chat_id, start_date, end_date)
                if messages:
                    chat_id = -chat_id  # Обновляем для сообщения об ошибке
            
            if not messages:
                await update.message.reply_text(
                    f"Сообщения не найдены в чате {chat_id} за указанный период."
                )
                return
            
            # Формируем экспорт
            export_text = self._format_export(messages, start_date, end_date)
            
            # Отправляем файл, если сообщение слишком длинное
            if len(export_text) > 4000:
                filename = f"export_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(export_text)
                
                try:
                    with open(filename, 'rb') as file:
                        await update.message.reply_document(
                            document=file,
                            filename=filename
                        )
                finally:
                    # Удаляем временный файл
                    if os.path.exists(filename):
                        os.remove(filename)
            else:
                await update.message.reply_text(export_text)
        
        except ValueError as e:
            await update.message.reply_text(f"Ошибка формата: {e}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при экспорте: {e}")
    
    def _format_export(self, messages: List[Message], start_date: datetime, 
                      end_date: datetime) -> str:
        """Форматирование экспорта сообщений"""
        export_lines = []
        export_lines.append("=" * 50)
        export_lines.append(f"ЭКСПОРТ СООБЩЕНИЙ")
        export_lines.append(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        export_lines.append(f"Всего сообщений: {len(messages)}")
        export_lines.append("=" * 50)
        export_lines.append("")
        
        for msg in messages:
            # Показываем дату сообщения и дату редактирования, если есть
            date_str = f"[{msg.message_date.strftime('%Y-%m-%d %H:%M:%S')}]"
            # Проверяем наличие edited_date (может быть None)
            if msg.edited_date:
                date_str += f" (отредактировано: {msg.edited_date.strftime('%Y-%m-%d %H:%M:%S')})"
            export_lines.append(date_str)
            
            if msg.user:
                user_info = f"{msg.user.first_name or ''} {msg.user.last_name or ''}".strip()
                if msg.user.username:
                    user_info += f" (@{msg.user.username})"
                export_lines.append(f"От: {user_info} (ID: {msg.user.id})")
            
            if msg.text:
                export_lines.append(f"Текст: {msg.text}")
            
            if msg.documents:
                export_lines.append("Файлы:")
                for doc in msg.documents:
                    doc_info = f"  - {doc.document_type}: {doc.file_name or doc.file_id}"
                    if doc.file_size:
                        doc_info += f" ({doc.file_size} байт)"
                    export_lines.append(doc_info)
            
            # Проверяем наличие реакций
            if hasattr(msg, 'reactions') and msg.reactions:
                # Группируем реакции по эмодзи и показываем количество
                reaction_counts = {}
                for r in msg.reactions:
                    emoji = r.emoji or "?"
                    reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1
                
                reactions_parts = []
                for emoji, count in reaction_counts.items():
                    if count > 1:
                        reactions_parts.append(f"{emoji} x{count}")
                    else:
                        reactions_parts.append(emoji)
                
                reactions_str = ", ".join(reactions_parts)
                export_lines.append(f"Реакции: {reactions_str} (всего: {len(msg.reactions)})")
            
            export_lines.append("-" * 50)
            export_lines.append("")
        
        return "\n".join(export_lines)
    
    def get_handlers(self):
        """Получение обработчиков команд для бота"""
        return [
            CommandHandler("start", self.start_command),
            CommandHandler("chats", self.chats_command),
            CommandHandler("export", self.export_command),
            CommandHandler("export_date", self.export_date_command),
        ]

