from sqlalchemy.orm import Session

from app.exceptions import (
    AccessDeniedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from app.models.user import User, UserRole
from app.repositories import interfaces
from app.repositories.users import UserRepository
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.users import UserCreate, UserRead, UserUpdate


class UserService:
    """Regras de negócio de usuários e credenciais."""

    def __init__(self, db: Session) -> None:
        self.repository: interfaces.UserRepository = UserRepository(db)

    def register(self, payload: UserCreate) -> UserRead:
        if self.repository.get_by_email(payload.email):
            raise ConflictError("email already registered")
        user = self.repository.create(
            User(
                full_name=payload.full_name,
                email=payload.email,
                hashed_password=hash_password(payload.password),
            )
        )
        return UserRead.model_validate(user)

    def authenticate(self, email: str, password: str) -> str:
        """Valida credenciais e devolve um token JWT, se corretas.

        Falha por usuário inexistente ou senha errada tem a mesma
        mensagem e o mesmo erro (evita enumeração de e-mails).
        """
        user = self.repository.get_by_email(email)
        generic_error = AuthenticationError("invalid credentials")
        if user is None:
            raise generic_error
        if not verify_password(password, user.hashed_password):
            raise generic_error
        return create_access_token(str(user.id))

    def require_user(self, token: str) -> User:
        """Resolve o token para um usuário autenticado, ou autentica falha."""
        user_id = decode_access_token(token)
        if user_id is None:
            raise AuthenticationError("invalid or expired token")
        user = self.repository.get_by_id(int(user_id))
        if user is None:
            # Token válido mas usuário removido: sessão inválida.
            raise AuthenticationError("invalid or expired token")
        return user

    def require_admin(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise AccessDeniedError("admin access required")

    def get(self, user_id: int, current_user: User) -> UserRead:
        """Consulta de usuário; o próprio usuário e ADMIN podem ver."""
        if user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise AccessDeniedError("access denied")
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return UserRead.model_validate(user)

    def list(self, offset: int, limit: int) -> list[UserRead]:
        return [UserRead.model_validate(u) for u in self.repository.list(offset, limit)]

    def update(self, user_id: int, payload: UserUpdate, current_user: User) -> UserRead:
        if user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise AccessDeniedError("access denied")
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.email is not None and payload.email != user.email:
            if self.repository.get_by_email(payload.email):
                raise ConflictError("email already registered")
            user.email = payload.email
        self.repository.update(user)
        return UserRead.model_validate(user)
