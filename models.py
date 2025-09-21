from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.ext.asyncio import AsyncAttrs

from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inbound_tag: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128), unique=True)
    level: Mapped[int] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(16))
    password: Mapped[str] = mapped_column(String(64), nullable=True)
    cipher_type: Mapped[int] = mapped_column(Integer, nullable=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=True)
    flow: Mapped[str] = mapped_column(String(32), default='xtls-rprx-vision')
    traffic: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reset_traffic_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expired_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, server_default=None)
