"""
Модуль для сбора сообщений из Telegram чатов
"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from database.db_manager import DatabaseManager


class MessageCollector:
    """Класс для сбора и сохранения сообщений из Telegram"""
    
    def __init__(self, db_manager: DatabaseManager):
        """Инициализация сборщика сообщений"""
        self.db_manager = db_manager
    
    async def handle_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отредактированных сообщений"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Проверяем, что это отредактированное сообщение
        if not update.edited_message:
            return
        
        # Пропускаем обычные сообщения (они обрабатываются в handle_message)
        if update.message and not update.edited_message:
            return
        
        message = update.edited_message
        chat = message.chat
        user = message.from_user
        
        
        # Пропускаем системные сообщения от ботов и анонимных пользователей
        if user:
            if user.is_bot:
                return
            if user.id == 1087968824:  # GroupAnonymousBot ID
                return
        
        try:
            # Сохраняем пользователя
            if user:
                self.db_manager.save_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            
            # Сохраняем чат
            chat_type = self._get_chat_type(chat.type)
            self.db_manager.save_chat(
                chat_id=chat.id,
                title=chat.title or chat.username or f"Chat {chat.id}",
                chat_type=chat_type
            )
            
            # Формируем текст сообщения (аналогично обычным сообщениям)
            message_text = message.text or message.caption
            
            # Обрабатываем опросы
            if message.poll:
                poll = message.poll
                poll_text = f"📊 Опрос: {poll.question}\n"
                if poll.options:
                    poll_text += "Варианты ответов:\n"
                    for option in poll.options:
                        poll_text += f"  - {option.text}\n"
                message_text = (message_text + "\n" + poll_text).strip() if message_text else poll_text
            
            # Обрабатываем геолокацию
            if message.location:
                location = message.location
                location_text = f"📍 Геолокация: широта {location.latitude}, долгота {location.longitude}"
                message_text = (message_text + "\n" + location_text).strip() if message_text else location_text
            
            # Обрабатываем место (venue)
            if message.venue:
                venue = message.venue
                venue_text = f"🏢 Место: {venue.title}"
                if venue.address:
                    venue_text += f"\nАдрес: {venue.address}"
                message_text = (message_text + "\n" + venue_text).strip() if message_text else venue_text
            
            # Обрабатываем контакты
            if message.contact:
                contact = message.contact
                contact_text = f"📞 Контакт: {contact.first_name}"
                if contact.last_name:
                    contact_text += f" {contact.last_name}"
                if contact.phone_number:
                    contact_text += f"\nТелефон: {contact.phone_number}"
                message_text = (message_text + "\n" + contact_text).strip() if message_text else contact_text
            
            # Получаем дату редактирования
            edited_date = None
            if hasattr(message, 'edit_date') and message.edit_date:
                edited_date = message.edit_date
                # Конвертируем в UTC
                if edited_date.tzinfo is not None:
                    edited_date = edited_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                # Если edit_date нет, используем текущее время
                edited_date = datetime.utcnow()
            
            # Сохраняем отредактированное сообщение
            if message.date:
                message_date = message.date
                if message_date.tzinfo is not None:
                    message_date = message_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                message_date = datetime.utcnow()
            
            self.db_manager.save_message(
                message_id=message.message_id,
                chat_id=chat.id,
                user_id=user.id if user else None,
                text=message_text,
                message_date=message_date,
                edited_date=edited_date
            )
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при обработке отредактированного сообщения: {e}", exc_info=True)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик входящих сообщений"""
        if not update.message:
            return
        
        message = update.message
        chat = message.chat
        user = message.from_user
        
        # Пропускаем служебные сообщения (создание группы, добавление участников и т.д.)
        if (message.new_chat_members or message.left_chat_member or 
            message.group_chat_created or message.supergroup_chat_created or 
            message.channel_chat_created or message.migrate_to_chat_id or 
            message.migrate_from_chat_id or message.new_chat_title or 
            message.new_chat_photo or message.delete_chat_photo or 
            message.pinned_message):
            return
        
        # Пропускаем сообщения без текста и без медиа (могут быть системными)
        if not message.text and not message.caption and not message.photo and not message.document and not message.video and not message.audio and not message.voice and not message.sticker and not message.video_note and not message.location and not message.venue and not message.contact and not message.poll:
            return
        
        # Пропускаем системные сообщения от ботов и анонимных пользователей
        if user:
            if user.is_bot:
                return
            # Пропускаем анонимных пользователей
            if user.id == 1087968824:  # GroupAnonymousBot ID
                return
        else:
            # Если нет информации о пользователе, это системное сообщение - пропускаем
            return
        
        try:
            # Сохраняем пользователя
            if user:
                self.db_manager.save_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            
            # Сохраняем чат
            chat_type = self._get_chat_type(chat.type)
            self.db_manager.save_chat(
                chat_id=chat.id,
                title=chat.title or chat.username or f"Chat {chat.id}",
                chat_type=chat_type
            )
            
            # Формируем текст сообщения, включая специальные типы
            message_text = message.text or message.caption
            
            # Обрабатываем опросы
            if message.poll:
                poll = message.poll
                poll_text = f"📊 Опрос: {poll.question}\n"
                if poll.options:
                    poll_text += "Варианты ответов:\n"
                    for option in poll.options:
                        poll_text += f"  - {option.text}\n"
                if poll.is_closed:
                    poll_text += "Опрос закрыт\n"
                if poll.is_anonymous:
                    poll_text += "Анонимный опрос\n"
                message_text = (message_text + "\n" + poll_text).strip() if message_text else poll_text
            
            # Обрабатываем геолокацию
            if message.location:
                location = message.location
                location_text = f"📍 Геолокация: широта {location.latitude}, долгота {location.longitude}"
                if location.live_period:
                    location_text += f" (живая геолокация, период: {location.live_period} сек)"
                if location.heading:
                    location_text += f", направление: {location.heading}°"
                message_text = (message_text + "\n" + location_text).strip() if message_text else location_text
            
            # Обрабатываем место (venue)
            if message.venue:
                venue = message.venue
                venue_text = f"🏢 Место: {venue.title}"
                if venue.address:
                    venue_text += f"\nАдрес: {venue.address}"
                if venue.foursquare_id:
                    venue_text += f"\nFoursquare ID: {venue.foursquare_id}"
                message_text = (message_text + "\n" + venue_text).strip() if message_text else venue_text
            
            # Обрабатываем контакты
            if message.contact:
                contact = message.contact
                contact_text = f"📞 Контакт: {contact.first_name}"
                if contact.last_name:
                    contact_text += f" {contact.last_name}"
                if contact.phone_number:
                    contact_text += f"\nТелефон: {contact.phone_number}"
                if contact.user_id:
                    contact_text += f"\nUser ID: {contact.user_id}"
                message_text = (message_text + "\n" + contact_text).strip() if message_text else contact_text
            
            # Обрабатываем голосовые сообщения (если нет текста)
            if message.voice and not message_text:
                voice = message.voice
                voice_text = f"🎤 Голосовое сообщение"
                if voice.duration:
                    voice_text += f" ({voice.duration} сек)"
                if voice.file_size:
                    voice_text += f", размер: {voice.file_size} байт"
                message_text = voice_text
            
            # Обрабатываем видеосообщения (если нет текста)
            if message.video_note and not message_text:
                video_note = message.video_note
                video_note_text = f"📹 Кружок (видеосообщение)"
                if video_note.duration:
                    video_note_text += f" ({video_note.duration} сек)"
                if video_note.length:
                    video_note_text += f", диаметр: {video_note.length}px"
                message_text = video_note_text
            
            # Проверяем, есть ли что сохранять (текст или медиа)
            has_content = bool(message_text) or message.photo or message.document or message.video or message.audio or message.voice or message.sticker or message.video_note or message.location or message.venue or message.contact or message.poll
            
            if not has_content:
                return
            
            # Сохраняем сообщение
            if message.date:
                message_date = message.date
                if message_date.tzinfo is not None:
                    message_date = message_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                message_date = datetime.utcnow()
            
            saved_message = self.db_manager.save_message(
                message_id=message.message_id,
                chat_id=chat.id,
                user_id=user.id if user else None,
                text=message_text,
                message_date=message_date
            )
            
            # Сохраняем документы/файлы
            if message.photo:
                # Для фото берем последнее (самое большое разрешение)
                photo = message.photo[-1]
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=photo.file_id,
                    file_unique_id=photo.file_unique_id,
                    file_size=photo.file_size,
                    document_type='photo'
                )
            
            if message.document:
                doc = message.document
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=doc.file_id,
                    file_unique_id=doc.file_unique_id,
                    file_name=doc.file_name,
                    mime_type=doc.mime_type,
                    file_size=doc.file_size,
                    document_type='document'
                )
            
            if message.video:
                video = message.video
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=video.file_id,
                    file_unique_id=video.file_unique_id,
                    file_name=video.file_name,
                    mime_type=video.mime_type,
                    file_size=video.file_size,
                    document_type='video'
                )
            
            if message.audio:
                audio = message.audio
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=audio.file_id,
                    file_unique_id=audio.file_unique_id,
                    file_name=audio.file_name,
                    mime_type=audio.mime_type,
                    file_size=audio.file_size,
                    document_type='audio'
                )
            
            if message.voice:
                voice = message.voice
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=voice.file_id,
                    file_unique_id=voice.file_unique_id,
                    mime_type=voice.mime_type,
                    file_size=voice.file_size,
                    document_type='voice'
                )
            
            if message.sticker:
                sticker = message.sticker
                mime_type = getattr(sticker, 'mime_type', None) or 'image/webp'
                file_size = getattr(sticker, 'file_size', None)
                self.db_manager.save_document(
                    message_db_id=saved_message.id,
                    file_id=sticker.file_id,
                    file_unique_id=sticker.file_unique_id,
                    mime_type=mime_type,
                    file_size=file_size,
                    document_type='sticker'
                )
            
            # Сохраняем реакции (если есть)
            reactions = None
            if hasattr(message, 'reactions') and message.reactions:
                reactions = message.reactions
            elif hasattr(message, 'reaction') and message.reaction:
                reactions = message.reaction if isinstance(message.reaction, list) else [message.reaction]
            
            if reactions:
                for reaction in reactions:
                    try:
                        emoji = None
                        user_id = None
                        
                        if hasattr(reaction, 'emoji'):
                            emoji = str(reaction.emoji)
                        elif hasattr(reaction, 'type') and hasattr(reaction.type, 'emoji'):
                            emoji = str(reaction.type.emoji)
                        elif isinstance(reaction, str):
                            emoji = reaction
                        
                        if hasattr(reaction, 'user_id'):
                            user_id = reaction.user_id
                        elif hasattr(reaction, 'user'):
                            user_id = reaction.user.id if hasattr(reaction.user, 'id') else None
                        
                        if emoji:
                            self.db_manager.save_reaction(
                                message_db_id=saved_message.id,
                                emoji=emoji,
                                user_id=user_id
                            )
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Не удалось сохранить реакцию: {e}")
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
    
    async def handle_message_reaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обновлений о реакциях на сообщения"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Проверяем наличие обновления о реакции
        if not hasattr(update, 'message_reaction') or not update.message_reaction:
            return
        
        try:
            reaction_update = update.message_reaction
            chat = reaction_update.chat
            user = reaction_update.user
            
            # Получаем информацию о реакции
            old_reactions = getattr(reaction_update, 'old_reaction', []) or []
            new_reactions = getattr(reaction_update, 'new_reaction', []) or []
            
            # Сохраняем пользователя
            if user:
                self.db_manager.save_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            
            # Находим сообщение в БД по message_id и chat_id
            session = self.db_manager.get_session()
            try:
                from database.models import Message, Reaction
                message = session.query(Message).filter(
                    Message.message_id == reaction_update.message_id,
                    Message.chat_id == chat.id
                ).first()
                
                if message:
                    # Удаляем старые реакции этого пользователя (если есть)
                    if old_reactions:
                        for old_reaction in old_reactions:
                            emoji = None
                            if hasattr(old_reaction, 'emoji'):
                                emoji = str(old_reaction.emoji)
                            elif hasattr(old_reaction, 'type') and hasattr(old_reaction.type, 'emoji'):
                                emoji = str(old_reaction.type.emoji)
                            
                            if emoji:
                                session.query(Reaction).filter(
                                    Reaction.message_id == message.id,
                                    Reaction.user_id == user.id,
                                    Reaction.emoji == emoji
                                ).delete()
                    
                    # Добавляем новые реакции
                    if new_reactions:
                        for new_reaction in new_reactions:
                            emoji = None
                            if hasattr(new_reaction, 'emoji'):
                                emoji = str(new_reaction.emoji)
                            elif hasattr(new_reaction, 'type') and hasattr(new_reaction.type, 'emoji'):
                                emoji = str(new_reaction.type.emoji)
                            
                            if emoji:
                                self.db_manager.save_reaction(
                                    message_db_id=message.id,
                                    emoji=emoji,
                                    user_id=user.id
                                )
                    session.commit()
            finally:
                session.close()
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при обработке реакции: {e}", exc_info=True)
    
    def _get_chat_type(self, chat_type: str) -> str:
        """Преобразование типа чата в строку"""
        type_mapping = {
            'private': 'private',
            'group': 'group',
            'supergroup': 'supergroup',
            'channel': 'channel'
        }
        return type_mapping.get(chat_type, 'unknown')

