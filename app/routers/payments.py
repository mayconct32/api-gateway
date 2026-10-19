from fastapi import APIRouter, Depends, status

from app.models.user import User
from app.schemas.payments import (
    CreatePaymentLinkRequest,
    PaymentLinkResponse,
    PaymentVerifyResponse,
    VerifyPaymentRequest,
)
from app.services.payments import PaymentService, build_payment_service
from app.services.users import get_current_user


router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/create-link", response_model=PaymentLinkResponse)
def create_payment(
    payload: CreatePaymentLinkRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(build_payment_service),
) -> PaymentLinkResponse:
    """Cria (ou reutiliza) o link de pagamento de um pedido.

    Idempotente por (pedido, provedor): pedir o mesmo pagamento
    novamente devolve o link já existente, sem nova cobrança.
    """
    return service.create_payment(current_user, payload)


@router.post("/verify", response_model=PaymentVerifyResponse)
def verify_payment(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentService = Depends(build_payment_service),
) -> PaymentVerifyResponse:
    """Confirmação solicitada na volta do gateway (URL de retorno).

    A validação real é feita contra o gateway (consulta direta), e os
    valores são comparados com o registrado no servidor. O webhook
    também pode confirmar o pagamento, de forma independente.
    """
    return service.verify_payment(current_user, payload)


@router.get("/success")
def payment_success() -> dict[str, str]:
    """Callback de sucesso da URL do gateway.

    Endpoint informativo: a confirmação oficial do pagamento acontece
    via POST /payments/verify ou webhook assinado, nunca por esta URL.
    """
    return {"message": "payment received; completion will be confirmed by validation"}


@router.get("/failed")
def payment_failed() -> dict[str, str]:
    """Callback de falha/cancelamento da URL do gateway."""
    return {"message": "payment was not completed"}
