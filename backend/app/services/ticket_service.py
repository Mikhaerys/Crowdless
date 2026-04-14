from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import date

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from python_http_client.exceptions import HTTPError

from app.core.config import settings
from app.models.booking import VisitorRegistrationRequest
from app.models.ticket import TicketResponse, TicketValidationResponse
from app.services.email_service import email_service
from app.services.firestore_service import FirestoreService
from app.utils.qr_generator import generate_qr_code_base64


class TicketService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def _calculate_age(self, birth_date: date, visit_date: date) -> int:
        return visit_date.year - birth_date.year - (
            (visit_date.month, visit_date.day) < (
                birth_date.month, birth_date.day)
        )

    def _infer_ticket_type(self, birth_date: date, visit_date: date) -> str:
        return "adult" if self._calculate_age(birth_date, visit_date) >= 18 else "child"

    def _sign_qr_payload(self, ticket_id: str, nonce: str) -> str:
        message = f"{ticket_id}:{nonce}".encode("utf-8")
        secret = settings.qr_signing_secret.encode("utf-8")
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def _build_qr_payload(self, ticket_id: str) -> str:
        nonce = secrets.token_urlsafe(12)
        signature = self._sign_qr_payload(ticket_id, nonce)
        return json.dumps(
            {
                "ticket_id": ticket_id,
                "nonce": nonce,
                "sig": signature,
            },
            separators=(",", ":"),
        )

    def _parse_qr_ticket_id(self, qr_payload: str) -> str:
        try:
            payload = json.loads(qr_payload)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid QR payload format",
            ) from error

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid QR payload format",
            )

        ticket_id = payload.get("ticket_id")
        if not isinstance(ticket_id, str) or not ticket_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="QR payload is missing ticket_id",
            )

        # Backward compatibility for previously issued tickets.
        if "sig" not in payload and "nonce" not in payload:
            return ticket_id

        nonce = payload.get("nonce")
        signature = payload.get("sig")
        if not isinstance(nonce, str) or not isinstance(signature, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="QR payload signature is incomplete",
            )

        expected_signature = self._sign_qr_payload(ticket_id, nonce)
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="QR payload signature is invalid",
            )

        return ticket_id

    def register_visitors(self, booking_id: str, payload: VisitorRegistrationRequest) -> list[TicketResponse]:
        booking_reference = self.firestore.bookings.document(booking_id)
        booking_snapshot = booking_reference.get()
        if not booking_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        booking = booking_snapshot.to_dict()
        visit_date = date.fromisoformat(booking["visit_date"])
        total_tickets = int(booking["total_tickets"])
        expected_adults = int(booking["adults"])
        expected_children = int(booking["children"])

        if booking.get("payment_status") != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment must be approved first",
            )
        if booking.get("reservation_status") != "reserved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking is not active",
            )
        if booking.get("tickets_created", 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Visitors are already registered",
            )
        if len(payload.visitors) != total_tickets:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Visitor count must match the number of tickets",
            )

        adult_visitors = 0
        child_visitors = 0

        existing_visitors = list(
            self.firestore.visitors.where(
                filter=FieldFilter("booking_id", "==", booking_id)
            )
            .limit(1)
            .stream()
        )
        if existing_visitors:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Visitors are already registered",
            )

        batch = self.firestore.client.batch()
        now = self.firestore.now()
        tickets: list[TicketResponse] = []

        for visitor in payload.visitors:
            expected_ticket_type = self._infer_ticket_type(
                visitor.birth_date, visit_date)
            if visitor.ticket_type != expected_ticket_type:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Visitor {visitor.name} does not match the purchased ticket type: "
                        f"expected {expected_ticket_type}, got {visitor.ticket_type}"
                    ),
                )

            if visitor.ticket_type == "adult":
                adult_visitors += 1
            else:
                child_visitors += 1

            visitor_reference = self.firestore.visitors.document()
            ticket_reference = self.firestore.tickets.document()

            visitor_data = {
                "booking_id": booking_id,
                "name": visitor.name,
                "birth_date": visitor.birth_date.isoformat(),
                "id_number": visitor.id_number,
                "ticket_type": visitor.ticket_type,
                "created_at": now,
            }
            qr_payload = self._build_qr_payload(ticket_reference.id)
            ticket_data = {
                "booking_id": booking_id,
                "visitor_id": visitor_reference.id,
                "visitor_name": visitor.name,
                "ticket_type": visitor.ticket_type,
                "qr_code": generate_qr_code_base64(qr_payload),
                "qr_payload": qr_payload,
                "validated": False,
                "validated_at": None,
                "created_at": now,
            }

            batch.set(visitor_reference, visitor_data)
            batch.set(ticket_reference, ticket_data)

            tickets.append(
                TicketResponse(
                    ticket_id=ticket_reference.id,
                    booking_id=booking_id,
                    visitor_id=visitor_reference.id,
                    visitor_name=visitor.name,
                    ticket_type=visitor.ticket_type,
                    qr_code=ticket_data["qr_code"],
                    qr_payload=qr_payload,
                    validated=False,
                    validated_at=None,
                )
            )

        if adult_visitors != expected_adults or child_visitors != expected_children:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Visitor ages do not match the purchased ticket distribution: "
                    f"expected {expected_adults} adult(s) and {expected_children} child(ren)"
                ),
            )

        batch.update(
            booking_reference,
            {
                "visitors_registered": len(payload.visitors),
                "tickets_created": len(payload.visitors),
                "contact_email": payload.contact_email,
                "updated_at": now,
            },
        )
        batch.commit()

        # ── Enviar email con todos los QRs ───────────────────
        try:
            email_service.send_tickets_email(
                to_email=payload.contact_email,
                visitor_name=payload.visitors[0].name,
                visit_date=booking["visit_date"],
                tickets=[
                    {
                        "ticket_id": ticket.ticket_id,
                        "visitor_name": ticket.visitor_name,
                        "ticket_type": ticket.ticket_type,
                        "qr_code": ticket.qr_code,
                    }
                    for ticket in tickets
                ],
            )
        except HTTPError as e:  # pyright: ignore[reportGeneralException]
            # Falla silenciosamente — tickets ya creados, QRs visibles en pantalla
            print(f"[email] Error al enviar email: {e}")

        return tickets

    def get_tickets_by_booking(self, booking_id: str) -> list[TicketResponse]:
        documents = self.firestore.tickets.where(
            filter=FieldFilter("booking_id", "==", booking_id)
        ).stream()
        tickets = []
        for document in documents:
            ticket = document.to_dict()
            tickets.append(
                TicketResponse(
                    ticket_id=document.id,
                    booking_id=ticket["booking_id"],
                    visitor_id=ticket["visitor_id"],
                    visitor_name=ticket["visitor_name"],
                    ticket_type=ticket.get("ticket_type", "adult"),
                    qr_code=ticket["qr_code"],
                    qr_payload=ticket["qr_payload"],
                    validated=bool(ticket["validated"]),
                    validated_at=ticket.get("validated_at"),
                )
            )
        return tickets

    def validate_ticket(self, ticket_id: str) -> TicketValidationResponse:
        ticket_reference = self.firestore.tickets.document(ticket_id)
        transaction = self.firestore.client.transaction()
        now = self.firestore.now()

        @firestore.transactional
        def validate(transaction: firestore.Transaction):
            ticket_snapshot = ticket_reference.get(transaction=transaction)
            if not ticket_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
                )

            ticket = ticket_snapshot.to_dict()
            if ticket.get("validated"):
                validated_at = ticket.get("validated_at")
                validated_at_text = (
                    validated_at.isoformat() if hasattr(
                        validated_at, "isoformat") else str(validated_at)
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ticket already validated (ticket_id={ticket_id}, validated_at={validated_at_text})",
                )

            booking_reference = self.firestore.bookings.document(
                ticket["booking_id"])
            booking_snapshot = booking_reference.get(transaction=transaction)
            if not booking_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
                )

            booking = booking_snapshot.to_dict()
            if booking.get("payment_status") != "approved":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Booking payment is not approved",
                )

            transaction.update(
                ticket_reference, {"validated": True, "validated_at": now}
            )
            ticket["validated"] = True
            ticket["validated_at"] = now
            return ticket

        ticket = validate(transaction)
        return TicketValidationResponse(
            ticket_id=ticket_id,
            booking_id=ticket["booking_id"],
            visitor_id=ticket["visitor_id"],
            visitor_name=ticket["visitor_name"],
            ticket_type=ticket.get("ticket_type", "adult"),
            validated=True,
            validated_at=ticket["validated_at"],
        )

    def validate_ticket_by_qr(self, qr_payload: str) -> TicketValidationResponse:
        ticket_id = self._parse_qr_ticket_id(qr_payload)
        return self.validate_ticket(ticket_id)

    def renew_ticket_qr(self, ticket_id: str) -> TicketResponse:
        """
        Invalida el QR actual y genera uno nuevo.
        Usado por el museo cuando un visitante reporta pérdida o fraude.
        """
        ticket_reference = self.firestore.tickets.document(ticket_id)
        ticket_snapshot = ticket_reference.get()

        if not ticket_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
            )

        ticket = ticket_snapshot.to_dict()

        if ticket.get("validated"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot renew a ticket that has already been used at the entrance")

        new_payload = self._build_qr_payload(ticket_id)
        new_qr_code = generate_qr_code_base64(new_payload)
        now = self.firestore.now()

        ticket_reference.update(
            {
                "qr_code": new_qr_code,
                "qr_payload": new_payload,
                "renewed_at": now,
                "updated_at": now,
            }
        )

        # Obtener el email de contacto del booking
        booking_reference = self.firestore.bookings.document(
            ticket["booking_id"])
        booking_snapshot = booking_reference.get()
        if booking_snapshot.exists:
            booking = booking_snapshot.to_dict()
            contact_email = booking.get("contact_email")
            if contact_email:
                try:
                    email_service.send_tickets_email(
                        to_email=contact_email,
                        visitor_name=ticket["visitor_name"],
                        visit_date=booking["visit_date"],
                        tickets=[
                            {
                                "ticket_id": ticket_id,
                                "visitor_name": ticket["visitor_name"],
                                "ticket_type": ticket.get("ticket_type", "adult"),
                                "qr_code": new_qr_code,
                            }
                        ],
                    )
                    print(f"[email] QR renovado enviado a {contact_email}")
                # pyright: ignore[reportGeneralException]
                except HTTPError as e:
                    print(f"[email] Error al reenviar email: {e}")

        return TicketResponse(
            ticket_id=ticket_id,
            booking_id=ticket["booking_id"],
            visitor_id=ticket["visitor_id"],
            visitor_name=ticket["visitor_name"],
            ticket_type=ticket.get("ticket_type", "adult"),
            qr_code=new_qr_code,
            qr_payload=new_payload,
            validated=bool(ticket["validated"]),
            validated_at=ticket.get("validated_at"),
        )
