from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.models.booking import PaymentResponse, PaymentVerificationRequest
from app.services.firestore_service import FirestoreService


class PaymentService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def verify_payment(self, booking_id: str, payload: PaymentVerificationRequest) -> PaymentResponse:
        booking_reference = self.firestore.bookings.document(booking_id)
        booking_snapshot = booking_reference.get()
        if not booking_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        booking = booking_snapshot.to_dict()
        if booking.get("reservation_status") == "released":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Booking is no longer active")
        if booking.get("payment_status") == "approved":
            payment_id = booking.get("payment_id")
            if not payment_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
            return self.get_payment(payment_id)

        now = self.firestore.now()
        payment_id = booking.get(
            "payment_id") or self.firestore.payments.document().id
        transaction_id = payload.transaction_id or f"TEST-{uuid.uuid4().hex[:12].upper()}"

        payment_data = {
            "booking_id": booking_id,
            "provider": payload.provider,
            "transaction_id": transaction_id,
            "amount": float(booking["amount"]),
            "currency": booking["currency"],
            "status": payload.status,
            "created_at": now,
        }
        self.firestore.payments.document(payment_id).set(payment_data)
        booking_reference.update(
            {
                "payment_id": payment_id,
                "payment_status": payload.status,
                "updated_at": now,
            }
        )
        return PaymentResponse(payment_id=payment_id, **payment_data)

    def get_payment(self, payment_id: str) -> PaymentResponse:
        payment_snapshot = self.firestore.payments.document(payment_id).get()
        if not payment_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        payment = payment_snapshot.to_dict()
        return PaymentResponse(payment_id=payment_snapshot.id, **payment)
