"""
SQLAlchemy модели для базы данных
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    messages = relationship("Message", back_populates="user")


class Chat(Base):
    """Модель чата/группы Telegram"""
    __tablename__ = 'chats'
    
    id = Column(BigInteger, primary_key=True)  # Telegram chat ID
    title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=True)  # 'private', 'group', 'supergroup', 'channel'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    messages = relationship("Message", back_populates="chat")


class Message(Base):
    """Модель сообщения из Telegram"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False)  # ID сообщения в Telegram
    chat_id = Column(BigInteger, ForeignKey('chats.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    text = Column(Text, nullable=True)
    message_date = Column(DateTime, nullable=False)
    edited_date = Column(DateTime, nullable=True)  # Дата последнего редактирования
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
    reactions = relationship("Reaction", back_populates="message", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="message", cascade="all, delete-orphan")


class Reaction(Base):
    """Модель реакции на сообщение"""
    __tablename__ = 'reactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    emoji = Column(String(50), nullable=True)
    user_id = Column(BigInteger, nullable=True)  # Кто поставил реакцию
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    message = relationship("Message", back_populates="reactions")


class Document(Base):
    """Модель документа/файла, прикрепленного к сообщению"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    file_id = Column(String(255), nullable=False)  # Telegram file_id
    file_unique_id = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    document_type = Column(String(50), nullable=True)  # 'photo', 'document', 'video', 'audio', 'voice', 'sticker'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    message = relationship("Message", back_populates="documents")

