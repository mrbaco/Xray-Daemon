from sqlalchemy import Integer, String, DateTime, Boolean, UniqueConstraint
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
    email: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(16))
    password: Mapped[str] = mapped_column(String(64), nullable=True)
    cipher_type: Mapped[int] = mapped_column(Integer, nullable=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=True)
    flow: Mapped[str] = mapped_column(String(32), nullable=True)
    traffic: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reset_traffic_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('inbound_tag', 'uuid', 'email', name='uix__inbound_tag__uuid__email'),
    )
