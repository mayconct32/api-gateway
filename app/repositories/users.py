from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.interfaces import UserRepository as UserRepositoryProtocol


class UserRepository(UserRepositoryProtocol):
    """Implementação SQLAlchemy de persistência de usuários."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """Recupera o usuário pelo id, ou None se inexistente."""
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Recupera o usuário pelo e-mail, ou None se inexistente."""
        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def create(self, user: User) -> User:
        """Persiste um novo usuário e devolve a instância recarregada."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        self.db.commit()
        self.db.refresh(user)
        return user

    def list(self, offset: int = 0, limit: int = 50) -> list[User]:
        """Lista paginada de usuários, ordenada por id."""
        statement = select(User).order_by(User.id).offset(offset).limit(limit)
        return list(self.db.scalars(statement))
