"""Utilitários de hash de senha e geração/verificação de tokens JWT."""

import bcrypt
import jwt
from datetime import UTC, datetime, timedelta

from app.config import get_settings


def hash_password(plain: str) -> str:
    """Gera hash bcrypt; o custo é o padrão da biblioteca (12)."""
    # A biblioteca bcrypt já embute um salt aleatório em cada hash.
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica a senha em claro contra o hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # Hash com formato inválido não deve travar a aplicação.
        return False


def create_access_token(subject: str) -> str:
    """Cria um JWT com o id do usuário no claim 'sub' e expiração."""
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": subject,
            "exp": datetime.now(UTC) + expires_delta,
        },
        settings.secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> str | None:
    """Retorna o id do usuário dos claims, ou None se inválido/expirado."""
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None
