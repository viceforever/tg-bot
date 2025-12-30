"""
Менеджер для работы с базой данных
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from typing import List
from config import config
from .models import Base, User, Chat, Message, Reaction, Document


class DatabaseManager:
    """Класс для управления подключением и операциями с БД"""
    
    def __init__(self):
        """Инициализация менеджера БД"""
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def _initialize_database(self):
        """Инициализация подключения к БД"""
        if self._initialized:
            return
        
        try:
            database_url = config.DATABASE_URL
            self.engine = create_engine(database_url, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine)
            self._initialized = True
        except Exception as e:
            print(f"Ошибка при подключении к БД: {e}")
            raise
    
    def create_tables(self):
        """Создание всех таблиц в БД"""
        if not self._initialized:
            self._initialize_database()
        
        try:
            Base.metadata.create_all(self.engine)
            print("Таблицы успешно созданы")
        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")
            raise
    
    def get_session(self) -> Session:
        """Получение сессии БД"""
        if not self._initialized:
            self._initialize_database()
        return self.SessionLocal()
    
    def save_user(self, user_id: int, username: str = None, 
                  first_name: str = None, last_name: str = None) -> User:
        """Сохранение или обновление пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                # Обновляем данные пользователя
                if username:
                    user.username = username
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
            else:
                # Создаем нового пользователя
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
            
            session.commit()
            return user
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при сохранении пользователя: {e}")
            raise
        finally:
            session.close()
    
    def save_chat(self, chat_id: int, title: str = None, chat_type: str = None) -> Chat:
        """Сохранение или обновление чата"""
        session = self.get_session()
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Сначала проверяем, есть ли чат с таким ID
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            
            if chat:
                # Обновляем существующий чат
                if title:
                    chat.title = title
                if chat_type:
                    chat.chat_type = chat_type
            else:
                # Если чата с таким ID нет, проверяем преобразование group -> supergroup
                if title and chat_type == 'supergroup':
                    # Ищем group с таким же названием
                    existing_group = session.query(Chat).filter(
                        Chat.title == title,
                        Chat.chat_type == 'group'
                    ).first()
                    
                    if existing_group:
                        # Обновляем старый group на supergroup и меняем ID
                        old_chat_id = existing_group.id
                        
                        # Сначала обновляем все сообщения, связанные со старым чатом
                        # Это нужно сделать ДО изменения ID чата, чтобы избежать нарушения foreign key
                        from .models import Message
                        from sqlalchemy import text
                        
                        messages_count = session.query(Message).filter(
                            Message.chat_id == old_chat_id
                        ).count()
                        
                        if messages_count > 0:
                            # Сначала создаем новый чат с новым ID
                            # Это нужно для того, чтобы foreign key constraint был удовлетворен
                            new_chat = Chat(id=chat_id, title=title, chat_type='supergroup')
                            session.add(new_chat)
                            session.flush()  # Сохраняем новый чат в БД
                            
                            # Теперь обновляем все сообщения на новый chat_id
                            session.execute(
                                text("UPDATE messages SET chat_id = :new_id WHERE chat_id = :old_id"),
                                {"new_id": chat_id, "old_id": old_chat_id}
                            )
                            session.flush()
                            
                            # Удаляем старый чат
                            session.delete(existing_group)
                            session.flush()
                            
                            chat = new_chat
                        else:
                            # Если сообщений нет, просто обновляем ID и тип чата
                            # Используем временный ID для обхода foreign key constraint
                            import random
                            temp_id = -abs(old_chat_id) - random.randint(1000000, 9999999)
                            
                            # Шаг 1: Обновляем чат на временный ID
                            session.execute(
                                text("UPDATE chats SET id = :temp_id WHERE id = :old_id"),
                                {"temp_id": temp_id, "old_id": old_chat_id}
                            )
                            session.flush()
                            
                            # Шаг 2: Обновляем на финальный ID и тип
                            session.execute(
                                text("UPDATE chats SET id = :new_id, chat_type = 'supergroup' WHERE id = :temp_id"),
                                {"new_id": chat_id, "temp_id": temp_id}
                            )
                            session.flush()
                            
                            chat = session.query(Chat).filter(Chat.id == chat_id).first()
                    else:
                        # Создаем новый чат
                        chat = Chat(
                            id=chat_id,
                            title=title,
                            chat_type=chat_type
                        )
                        session.add(chat)
                else:
                    # Создаем новый чат
                    chat = Chat(
                        id=chat_id,
                        title=title,
                        chat_type=chat_type
                    )
                    session.add(chat)
            
            session.commit()
            return chat
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при сохранении чата: {e}")
            raise
        finally:
            session.close()
    
    def save_message(self, message_id: int, chat_id: int, user_id: int = None,
                    text: str = None, message_date: datetime = None, 
                    edited_date: datetime = None) -> Message:
        """Сохранение сообщения"""
        session = self.get_session()
        try:
            # Проверяем, существует ли уже такое сообщение
            existing = session.query(Message).filter(
                Message.message_id == message_id,
                Message.chat_id == chat_id
            ).first()
            
            if existing:
                # Если это редактирование, обновляем текст и дату редактирования
                if edited_date is not None:
                    if text is not None:
                        existing.text = text
                    
                    # Убеждаемся, что дата редактирования в UTC
                    if edited_date.tzinfo is not None:
                        edited_date = edited_date.astimezone(timezone.utc).replace(tzinfo=None)
                    existing.edited_date = edited_date
                    session.commit()
                    session.refresh(existing)
                return existing
            
            # Убеждаемся, что дата в UTC и без timezone info
            if message_date and message_date.tzinfo is not None:
                message_date = message_date.astimezone(timezone.utc).replace(tzinfo=None)
            elif not message_date:
                message_date = datetime.utcnow()
            
            # Обрабатываем дату редактирования
            if edited_date and edited_date.tzinfo is not None:
                edited_date = edited_date.astimezone(timezone.utc).replace(tzinfo=None)
            
            message = Message(
                message_id=message_id,
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                message_date=message_date,
                edited_date=edited_date
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при сохранении сообщения: {e}")
            raise
        finally:
            session.close()
    
    def save_reaction(self, message_db_id: int, emoji: str = None, 
                     user_id: int = None) -> Reaction:
        """Сохранение реакции на сообщение"""
        session = self.get_session()
        try:
            reaction = Reaction(
                message_id=message_db_id,
                emoji=emoji,
                user_id=user_id
            )
            session.add(reaction)
            session.commit()
            return reaction
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при сохранении реакции: {e}")
            raise
        finally:
            session.close()
    
    def save_document(self, message_db_id: int, file_id: str, 
                     file_unique_id: str = None, file_name: str = None,
                     mime_type: str = None, file_size: int = None,
                     document_type: str = None) -> Document:
        """Сохранение документа/файла"""
        session = self.get_session()
        try:
            document = Document(
                message_id=message_db_id,
                file_id=file_id,
                file_unique_id=file_unique_id,
                file_name=file_name,
                mime_type=mime_type,
                file_size=file_size,
                document_type=document_type
            )
            session.add(document)
            session.commit()
            return document
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Ошибка при сохранении документа: {e}")
            raise
        finally:
            session.close()
    
    def get_messages_by_date_range(self, chat_id: int, start_date: datetime, 
                                   end_date: datetime) -> List[Message]:
        """Получение сообщений за указанный период"""
        session = self.get_session()
        try:
            # Загружаем сообщения вместе с связанными объектами (user, documents, reactions)
            messages = session.query(Message).options(
                joinedload(Message.user),
                joinedload(Message.documents),
                joinedload(Message.reactions)
            ).filter(
                Message.chat_id == chat_id,
                Message.message_date >= start_date,
                Message.message_date <= end_date
            ).order_by(Message.message_date).all()
            
            return messages
        except SQLAlchemyError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при получении сообщений: {e}")
            raise
        finally:
            session.close()
    
    def get_chat_list(self) -> List[Chat]:
        """Получение списка всех чатов"""
        session = self.get_session()
        try:
            chats = session.query(Chat).all()
            return chats
        except SQLAlchemyError as e:
            print(f"Ошибка при получении списка чатов: {e}")
            raise
        finally:
            session.close()

