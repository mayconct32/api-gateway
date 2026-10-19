from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import get_current_user, get_user_service
from app.models.user import User
from app.services.users import UserService
from app.schemas.users import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    """Cadastro público de usuário com papel comum (USER)."""
    return service.register(payload)


@router.post("/auth/token")
def login_for_access_token(
    form: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    """Login por e-mail (campo username) e senha; devolve JWT Bearer."""
    return {
        "access_token": service.authenticate(form.username, form.password),
        "token_type": "bearer",
    }


@router.get("/users/me", response_model=UserRead)
def read_me(current_user=Depends(get_current_user)) -> UserRead:
    """Dados do usuário autenticado."""
    return UserRead.model_validate(current_user)


@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    """Consulta de usuário; dono ou ADMIN."""
    return service.get(user_id, current_user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    """Atualização de dados básicos (nome/email); dono ou ADMIN."""
    return service.update(user_id, payload, current_user)


@router.get("/users", response_model=list[UserRead])
def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    """Listagem de usuários (ADMIN); paginação skip/limit."""
    service.require_admin(current_user)
    return service.list(skip, limit)
