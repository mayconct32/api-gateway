from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.repositories.users import UserRepository
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.users import UserCreate, UserRead, UserUpdate


# O token é enviado como Bearer no header Authorization (OAuth2PasswordBearer
# substitui a implementação manual no request, já que usamos JWT próprio).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class UserService:
    """Regras de negócio de usuários e credenciais."""

    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)

    def register(self, payload: UserCreate) -> UserRead:
        if self.repository.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email already registered",
            )
        user = self.repository.create(
            User(
                full_name=payload.full_name,
                email=payload.email,
                hashed_password=hash_password(payload.password),
            )
        )
        return UserRead.model_validate(user)

    def authenticate(self, email: str, password: str) -> str:
        """Valida credenciais e devolve um token JWT, se corretas."""
        user = self.repository.get_by_email(email)
        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if user is None:
            raise generic_error
        if not verify_password(password, user.hashed_password):
            raise generic_error
        return create_access_token(str(user.id))

    def require_user(self, token: str) -> User:
        """Resolve o token para um usuário autenticado (401/404 possíveis)."""
        user_id = decode_access_token(token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = self.repository.get_by_id(int(user_id))
        if user is None:
            # Token válido mas usuário removido: sessão inválida.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def require_admin(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin access required",
            )

    def get(self, user_id: int, current_user: User) -> UserRead:
        """Consulta de usuário; o próprio usuário e ADMIN podem ver."""
        if user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access denied")
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        return UserRead.model_validate(user)

    def list(self, offset: int, limit: int) -> list[UserRead]:
        return [UserRead.model_validate(u) for u in self.repository.list(offset, limit)]

    def update(self, user_id: int, payload: UserUpdate, current_user: User) -> UserRead:
        if user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="access denied")
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.email is not None and payload.email != user.email:
            if self.repository.get_by_email(payload.email):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="email already registered",
                )
            user.email = payload.email
        self.repository.update(user)
        return UserRead.model_validate(user)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependência FastAPI: usuário autenticado a partir do token Bearer."""
    return UserService(db).require_user(token)


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependência FastAPI: exige papel ADMIN para rotas administrativas."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return current_user


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)
