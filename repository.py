from typing import Literal
from sqlalchemy.orm import Session
from sqlalchemy import select
from payment import Payment


# faça uma interface para o repository. Quem sabe eu nao mudo de ORM para alguma outra abordagem...
class PaymentRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update(self, payment: Payment) -> Payment:
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_pending_by_orrder_and_provider(self, order_id: int, provider: str) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.provider == provider,
                Payment.status == Literal["PENDING"] # padronize utilizando ENUM em todas os valores literais da aplicaçao
            )
        )
        return self.db.scalars(statement).first()

    def get_by_order_and_provider(self, order_id: int, provider: str) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.provider == provider,
            ).order_by(Payment.id.desc())
        )
        return self.db.scalars(statement).first()
