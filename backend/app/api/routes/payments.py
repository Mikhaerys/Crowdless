from fastapi import APIRouter

from app.models.booking import PaymentResponse, PaymentVerificationRequest
from app.services.runtime import payment_service, reservation_service


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{booking_id}/verify", response_model=PaymentResponse)
def verify_payment(booking_id: str, payload: PaymentVerificationRequest) -> PaymentResponse:
    payment = payment_service.verify_payment(booking_id, payload)
    if payload.status in {"failed", "cancelled"}:
        reservation_service.release_capacity(booking_id)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str) -> PaymentResponse:
    return payment_service.get_payment(payment_id)
