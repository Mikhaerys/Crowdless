from fastapi import APIRouter

from app.models.booking import (
    BoldPaymentPreparationResponse,
    BoldPaymentVerificationRequest,
    PaymentResponse,
    PaymentVerificationRequest,
)
from app.services.runtime import payment_service, reservation_service


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{booking_id}/verify", response_model=PaymentResponse)
def verify_payment(booking_id: str, payload: PaymentVerificationRequest) -> PaymentResponse:
    payment = payment_service.verify_payment(booking_id, payload)
    if payload.status in {"failed", "cancelled"}:
        reservation_service.release_capacity(booking_id)
    return payment


@router.post("/{booking_id}/bold/prepare", response_model=BoldPaymentPreparationResponse)
def prepare_bold_payment(booking_id: str) -> BoldPaymentPreparationResponse:
    return payment_service.prepare_bold_payment(booking_id)


@router.post("/bold/verify", response_model=PaymentResponse)
def verify_bold_payment(payload: BoldPaymentVerificationRequest) -> PaymentResponse:
    payment = payment_service.verify_bold_payment(payload)
    if payment.status in {"failed", "cancelled"}:
        reservation_service.release_capacity(payload.booking_id)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str) -> PaymentResponse:
    return payment_service.get_payment(payment_id)
