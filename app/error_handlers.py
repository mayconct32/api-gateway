"""Tradução de exceções de domínio para respostas HTTP.

Único ponto da aplicação que conhece, de um lado, as exceções de
negócio (app/exceptions.py) e, do outro, o formato de erro da API.
Adicionar um domínio de exceção novo exige apenas um mapa abaixo; os
serviços permanecem livres de conceitos HTTP.
"""

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    AccessDeniedError,
    AuthenticationError,
    ConflictError,
    DomainError,
    InvalidOperationError,
    NotFoundError,
    PaymentProviderUnavailableError,
)

# Cada exceção de domínio tem um status HTTP e, opcionalmente, headers
# de resposta associados (ex.: WWW-Authenticate para erros de autenticação).
_STATUS_BY_EXCEPTION: list[tuple[type[DomainError], int, Callable[[], dict[str, str]]]] = [
    (NotFoundError, 404, dict),
    (ConflictError, 409, dict),
    (InvalidOperationError, 400, dict),
    (PaymentProviderUnavailableError, 502, dict),
    (AccessDeniedError, 403, dict),
    (AuthenticationError, 401, lambda: {"WWW-Authenticate": "Bearer"}),
]


def _response_for(exc: DomainError) -> JSONResponse:
    """Resolve status e headers pelo tipo concreto da exceção."""
    for exception_type, status_code, headers_factory in _STATUS_BY_EXCEPTION:
        if type(exc) is exception_type:
            return JSONResponse(
                content={"detail": str(exc)},
                status_code=status_code,
                headers=headers_factory() or None,
            )
    return JSONResponse(content={"detail": str(exc)}, status_code=400)


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    """Handler FastAPI: converte DomainError (e subclasses) em JSON response."""
    return _response_for(exc)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra o handler de exceções de domínio na aplicação."""
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
