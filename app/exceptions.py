"""Exceções de domínio da aplicação.

Os serviços devem sinalizar falhas de regra de negócio, autorização,
recursos e dependências externas através destas exceções — nunca de
exceções HTTP. A tradução para respostas HTTP (status code e payload)
acontece na borda da aplicação: app/error_handlers.py registra os
handlers no FastAPI, mantendo a camada de negócio agnóstica de
framework.
"""


class DomainError(Exception):
    """Base para todas as exceções de domínio.

    A mensagem é diretamente apropriada para exposição ao cliente em
    formato de resposta de erro: não deve conter detalhes internos
    (stack traces, segredos, identificadores internos do gateway).
    """


class NotFoundError(DomainError):
    """Recurso solicitado não existe (ou está fora do escopo do autor)."""


class ConflictError(DomainError):
    """Estado atual do recurso conflita com a operação solicitada."""


class AuthenticationError(DomainError):
    """Credenciais ausentes, inválidas ou expiradas."""


class AccessDeniedError(DomainError):
    """Recurso existente, porém sem permissão para esta operação/auth."""


class InvalidOperationError(DomainError):
    """Operação válida, porém recusada pelas regras de negócio."""


class PaymentProviderUnavailableError(DomainError):
    """Provedor de pagamento indisponível ou com falha de comunicação.

    Erro do ambiente/dependência externa, não do cliente; lança-se no
    lugar de qualquer PaymentGatewayError capturado dos gateways.
    """
