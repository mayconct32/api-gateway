from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from dotenv import load_dotenv

import os 

from schemas import CreatePaymentLinkRequest, PaymentLinkresponse
from repository import PaymentRepository, OrderRepository
from schemas import CreatePaymentLinkRequest, UserRole
from payment import Payment
from user_model import User
from provider import RazorpayProvider


load_dotenv()


# essas classes de schemas do pydantic estao estao no lugar errado, e algumas estao inacabadas. Por favor, faça esse ajuste

class VerifyPaymentRequest(BaseModel):
    order_id: int,
    provider: PaymentProvider,
    payment_id: int


class PaymentVerifyResponse(BaseModel):
    order_id: int,
    payment_status: PaymentStatus,
    order_status: OrderStatus,
    provider: PaymentProvider,
    payment_id: str


class PaymentService:
    # classe que contém os serviços de pagamento
    def __init_(self, db: Session, payment_provider: PaymentProvider):
        #instanciando as classes para interagir com o banco de dados
        self.order_repository = OrderRepository(db)
        self.payment_repository = PaymentRepository(db)
        # O provider será o usuário que escolherá, é bom fazer uma 
        # validaçao para saber se o usuário escolheu uma opçao 
        # válida(Razorpay ou stripe). No Brasil, acredito que nao 
        # há como utilizar o Razor, logo, dê enfase no stripe
        self.payment_provider = payment_provider

    # nao parece ser a melhor aboradagem utilizar "@property"
    @property
    def _get_provider(self):
        return self.payment_provider

    def _get_owned_order(self, order_id: int, current_user: User):
        #buscar pedido por id
        order = self.order_repository.get_by_id(order_id)

        #verificar so o pedido nao existe
        if order is None:
            #implementaçao ruim(misturando escopos)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="order not found"
            )

        #verifica se o usuario tem o mesmo id do criador do pedido e se ele nao é o ADMIN
        if order.user_id != current_user.id and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="access denied"
            )

        return order

    #vai retornar o link e as informaçoes do pedido
    def create_payment(self, current_user: User, payload: CreatePaymentLinkRequest) -> PaymentLinkresponse:
        order = self._get_owned_order(payload.order_id, current_user)

        # só pode pagar os pedidos que estao pendentes 
        if order.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment link can be created for pending order"
            )

        # verificar se o pedido já foi pago
        if order.payment_status == "PAID":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order is already paid"
            )

        # buscar pedido pendente de acordo com o provedor
        existing_payment = self.payment_repository.get_pending_by_orrder_and_provider(
            order.id,
            payload.provider.value
        )

        # verifica se já existe um pagamento pendente. Se sim, retorne-o
        if existing_payment is not None:
            return PaymentLinkresponse(
                order_id=order.id,
                provider=payload.provider,
                amount=existing_payment.amount,
                currency=existing_payment.currency,
                payment_link=existing_payment.currency,
                provider_payment_link_id=existing_payment.provider_payment_link_id
            )

        # aqui estamos passando o provedor escolhido(o que está dentro do payload)
        provider = self._get_provider(payload.provider)

        provider_response = provider.create_payment_link(
            order_id=order.id,
            amount=order.total_amount,
            user_name=current_user.full_name,
            user_email=current_user.email
        )

        #Senao, crie-o
        payment = Payment(
            order_id=order.id,
            User_id=current_user.id,
            provider=payload.provider.value,
            amount=order.total_amount,
            currency="INR", #moeda de exemplo
            status="PENDING",
            payment_link_url=provider_response["payment_link"],
            provider_payment_link_id=provider_response["provider_payment_link_id"]
        )

        #armazena pedido
        db_payment = self.payment_repository.create(payment)

        return PaymentLinkresponse(
            order_id=order.id,
            provider=payload.provider,
            amount=db_payment.amount,
            currency=db_payment.currency,
            payment_link=db_payment.payment_link_url,
            provider_payment_link_id=db_payment.provider_payment_link_id
        )

    def verify_payment(self, current_user: User, payload: VerifyPaymentRequest) -> dict:
        order = self._get_owned_order(payload.order_id, current_user)

        payment = self.payment_repository.get_by_order_and_provider(
            order.id,
            payload.provider.value
        )

        if payment is None:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail="payment not found"
            )

        if payment.status == "PAID":
            return  PaymentVerifyResponse(
                order_id=order.id,
                payment_status="PAID",
                order_status=order.status,
                provider=payload.provider,
                payment_id=payment.provider_payment_id or payload.payment_id
            ).model_dump()

        provider=self._get_provider(payload.provider)
        provider_payment=provider.get_payment_details(payload.payment_id)
        expected_amount=order.total_amount*100

        if provider_payment["amount"] != expected_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment amount does not match order amount"
            )

        if not provider_payment["is_paid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment not completed"
            )

        payment.status="PAID"
        payment.provider_payment_id=provider_payment["payment_id"]
        self.payment_repository.update(payment)

        order.payment_status="PAID"
        order.status=OrderStatus.CONFIRMED.value
        self.order_repository.update(order)

        return PaymentVerifyResponse(
            order_id=order.id,
            payment_status="PAID",
            order_status=order.status,
            provider=payload.provider,
            payment_id=payment.provider_payment_id
        ).model_dump()


