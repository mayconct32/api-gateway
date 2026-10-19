from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, Enum):
    """Papéis de usuário (segurança: autenticação e operações admin)."""

    USER = "user"
    ADMIN = "admin"


class User(Base):
    """Usuário autenticável, com papel USER ou ADMIN."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False, validate_strings=True),
        nullable=False,
        default=UserRole.USER,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
