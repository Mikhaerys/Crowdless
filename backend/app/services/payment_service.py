from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

import requests

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.booking import (
    BoldPaymentPreparationResponse,
    BoldPaymentVerificationRequest,
    PaymentResponse,
    PaymentVerificationRequest,
)
from app.services.firestore_service import FirestoreService


class PaymentService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def prepare_bold_payment(self, booking_id: str) -> BoldPaymentPreparationResponse:
        if not settings.bold_api_key or not settings.bold_secret_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bold integration is not configured",
            )

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")

        amount = int(round(float(booking.get("amount", 0))))
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Booking amount must be greater than zero",
            )

        currency = str(booking.get("currency") or "COP").upper()
        order_id = f"{booking_id}-{int(datetime.utcnow().timestamp() * 1000)}"
        integrity_signature = self.generate_integrity_hash(
            order_id, amount, currency)
        redirection_url = f"{settings.frontend_app_url}/pago"

        booking_reference.update(
            {
                "bold_order_id": order_id,
                "updated_at": self.firestore.now(),
            }
        )

        return BoldPaymentPreparationResponse(
            booking_id=booking_id,
            order_id=order_id,
            api_key=settings.bold_api_key,
            amount=amount,
            currency=currency,
            integrity_signature=integrity_signature,
            description=f"Reserva Crowdless {booking_id}",
            redirection_url=redirection_url,
        )

    def generate_integrity_hash(self, order_id: str, amount: int, currency: str) -> str:
        if not settings.bold_secret_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bold secret key is not configured",
            )
        raw_value = f"{order_id}{amount}{currency}{settings.bold_secret_key}"
        return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

    def verify_bold_payment(self, payload: BoldPaymentVerificationRequest) -> PaymentResponse:
        booking_reference = self.firestore.bookings.document(
            payload.booking_id)
        booking_snapshot = booking_reference.get()
        if not booking_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        booking = booking_snapshot.to_dict()
        if booking.get("payment_status") == "approved":
            payment_id = booking.get("payment_id")
            if not payment_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
            return self.get_payment(payment_id)

        if not payload.bold_order_id.startswith(payload.booking_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The order id does not belong to this booking",
            )

        tx_data = self._fetch_bold_transaction(payload.bold_order_id)
        tx_status = tx_data.get("payment_status") or payload.bold_tx_status
        normalized_status = self._normalize_bold_status(tx_status)
        transaction_id = payload.transaction_id or tx_data.get(
            "transaction_id") or payload.bold_order_id

        now = self.firestore.now()
        payment_id = booking.get(
            "payment_id") or self.firestore.payments.document().id
        payment_data = {
            "booking_id": payload.booking_id,
            "provider": "bold",
            "transaction_id": transaction_id,
            "amount": float(booking["amount"]),
            "currency": booking["currency"],
            "status": normalized_status,
            "created_at": now,
            "bold_order_id": payload.bold_order_id,
            "bold_tx_status": tx_status,
        }

        self.firestore.payments.document(payment_id).set(payment_data)
        booking_reference.update(
            {
                "payment_id": payment_id,
                "payment_status": normalized_status,
                "updated_at": now,
            }
        )
        return PaymentResponse(payment_id=payment_id, **payment_data)

    def _fetch_bold_transaction(self, order_id: str) -> dict:
        if not settings.bold_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bold api key is not configured",
            )

        endpoint = f"{settings.bold_api_url}/payment-voucher/{order_id}"
        headers = {"Authorization": f"x-api-key {settings.bold_api_key}"}
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to query Bold transaction status",
            ) from exc

        if response.status_code in {401, 403}:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Bold credentials were rejected",
            )
        if response.status_code == 404:
            return {}
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Bold returned an unexpected error",
            )

        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _normalize_bold_status(self, status_value: str | None) -> str:
        status_key = (status_value or "").strip().upper()
        mapping = {
            "APPROVED": "approved",
            "PENDING": "pending",
            "PROCESSING": "processing",
            "REJECTED": "failed",
            "FAILED": "failed",
            "VOIDED": "cancelled",
            "CANCELLED": "cancelled",
            "CANCELED": "cancelled",
            "NO_TRANSACTION_FOUND": "pending",
        }
        return mapping.get(status_key, "failed")

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
