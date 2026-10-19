from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.enums import PaymentProviderEnum
from app.services.payments import get_providers
from app.services.payments import PaymentService, build_payment_service


router = APIRouter(prefix="/api/v1/payments/webhooks", tags=["webhooks"])

# Cabeçalho de assinatura por provedor.
SIGNATURE_HEADERS = {
    PaymentProviderEnum.STRIPE: "stripe-signature",
    PaymentProviderEnum.RAZORPAY: "x-razorpay-signature",
}


@router.post("/{provider}")
async def payment_webhook(
    provider: PaymentProviderEnum,
    request: Request,
    service: PaymentService = Depends(build_payment_service),
    providers: dict[PaymentProviderEnum, Any] = Depends(get_providers),
) -> dict[str, str]:
    """Recebe webhooks Stripe/Razorpay com verificação de assinatura.

    O corpo cru (bytes) é necessário: a assinatura HMAC calcula-se sobre
    o payload exatamente como enviado. Assinatura inválida rejeita a
    chamada (403) antes de qualquer leitura dos dados.
    """
    provider_instance = providers.get(provider)
    if provider_instance is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="payment provider is not available",
        )

    payload = await request.body()
    signature = request.headers.get(SIGNATURE_HEADERS[provider], "")

    # A verificação acontece dentro do provedor (cada gateway tem seu
    # esquema de assinatura); erro -> 403, sem expor detalhes internos.
    try:
        event: Any = provider_instance.verify_webhook_signature(payload, signature)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid webhook signature",
        ) from None

    return service.handle_webhook(provider, event)
