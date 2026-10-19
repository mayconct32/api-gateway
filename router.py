from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from schemas import CreatePaymentLinkRequest, PaymentLinkResponse
from user_model import User
from service import PaymentService, VerifyPaymentRequest


payment = APIRouter(tags=["Payments"], prefix="/payments")


@payment.post("/create-link", response_model = PaymentLinkResponse)
def create_payment(
    payload: CreatePaymentLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    #implementaçao ruim(o ideal seria utilizar inject)
    #faça uma correçao aqui também
    service = PaymentService(db)
    return service.create_payment(current_user, payload)


@payment.post("/verify", response_model = dict)
def verify_payment(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    #implementaçao ruim(o ideal seria utilizar inject)
    #faça uma correçao aqui também
    service = PaymentService(db)
    return service.verify_payment(current_user, payload)

