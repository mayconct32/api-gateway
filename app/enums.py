from enum import Enum


class PaymentProviderEnum(str, Enum):
    """Provedores de pagamento suportados (usados no payload e no BD)."""

    RAZORPAY = "razorpay"
    STRIPE = "stripe"


class PaymentStatus(str, Enum):
    """Estados possíveis de um Payment, gravados no BD como string."""

    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"


class OrderStatus(str, Enum):
    """Estados possíveis de um Order, gravados no BD como string."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
