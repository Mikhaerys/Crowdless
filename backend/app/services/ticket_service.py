from __future__ import annotations

import json
import time

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from app.models.booking import VisitorRegistrationRequest
from app.models.ticket import TicketResponse, TicketValidationResponse
from app.services.firestore_service import FirestoreService
from app.utils.qr_generator import generate_qr_code_base64


class TicketService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def register_visitors(self, booking_id: str, payload: VisitorRegistrationRequest) -> list[TicketResponse]:
        booking_reference = self.firestore.bookings.document(booking_id)
        booking_snapshot = booking_reference.get()
        if not booking_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        booking = booking_snapshot.to_dict()
        total_tickets = int(booking["total_tickets"])
        if booking.get("payment_status") != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Payment must be approved first")
        if booking.get("reservation_status") != "reserved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Booking is not active")
        if booking.get("tickets_created", 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Visitors are already registered")
        if len(payload.visitors) != total_tickets:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Visitor count must match the number of tickets",
            )

        existing_visitors = list(
            self.firestore.visitors.where(filter=FieldFilter(
                "booking_id", "==", booking_id)).limit(1).stream()
        )
        if existing_visitors:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Visitors are already registered")

        batch = self.firestore.client.batch()
        now = self.firestore.now()
        tickets: list[TicketResponse] = []

        for visitor in payload.visitors:
            visitor_reference = self.firestore.visitors.document()
            ticket_reference = self.firestore.tickets.document()
            visitor_data = {
                "booking_id": booking_id,
                "name": visitor.name,
                "birth_date": visitor.birth_date.isoformat(),
                "id_number": visitor.id_number,
                "created_at": now,
            }
            qr_payload = json.dumps(
                {
                    "ticket_id": ticket_reference.id,
                    "booking_id": booking_id,
                    "visitor_id": visitor_reference.id,
                    "visit_date": booking["visit_date"],
                },
                separators=(",", ":"),
            )
            ticket_data = {
                "booking_id": booking_id,
                "visitor_id": visitor_reference.id,
                "visitor_name": visitor.name,
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
                    qr_code=ticket_data["qr_code"],
                    qr_payload=qr_payload,
                    validated=False,
                    validated_at=None,
                )
            )

        batch.update(
            booking_reference,
            {
                "visitors_registered": len(payload.visitors),
                "tickets_created": len(payload.visitors),
                "updated_at": now,
            },
        )
        batch.commit()
        return tickets

    def get_tickets_by_booking(self, booking_id: str) -> list[TicketResponse]:
        documents = self.firestore.tickets.where(
            filter=FieldFilter("booking_id", "==", booking_id)).stream()
        tickets = []
        for document in documents:
            ticket = document.to_dict()
            tickets.append(
                TicketResponse(
                    ticket_id=document.id,
                    booking_id=ticket["booking_id"],
                    visitor_id=ticket["visitor_id"],
                    visitor_name=ticket["visitor_name"],
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
                    status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

            ticket = ticket_snapshot.to_dict()
            if ticket.get("validated"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Ticket already validated")

            booking_reference = self.firestore.bookings.document(
                ticket["booking_id"])
            booking_snapshot = booking_reference.get(transaction=transaction)
            if not booking_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

            booking = booking_snapshot.to_dict()
            if booking.get("payment_status") != "approved":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Booking payment is not approved")

            transaction.update(ticket_reference, {
                               "validated": True, "validated_at": now})
            ticket["validated"] = True
            ticket["validated_at"] = now
            return ticket

        ticket = validate(transaction)
        return TicketValidationResponse(
            ticket_id=ticket_id,
            booking_id=ticket["booking_id"],
            visitor_id=ticket["visitor_id"],
            visitor_name=ticket["visitor_name"],
            validated=True,
            validated_at=ticket["validated_at"],
        )

    def renew_ticket_qr(self, ticket_id: str) -> TicketResponse:
        ticket_reference = self.firestore.tickets.document(ticket_id)
        ticket_snapshot = ticket_reference.get()

        if not ticket_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        ticket = ticket_snapshot.to_dict()

        if ticket.get("validated"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot renew a ticket that has already been used at the entrance")

        original_payload = json.loads(ticket["qr_payload"])
        new_payload = json.dumps(
            {
                "ticket_id": original_payload["ticket_id"],
                "booking_id": original_payload["booking_id"],
                "visitor_id": original_payload["visitor_id"],
                "visit_date": original_payload["visit_date"],
                "renewed_at": int(time.time()),
            },
            separators=(",", ":"),
        )
        new_qr_code = generate_qr_code_base64(new_payload)
        now = self.firestore.now()

        ticket_reference.update({
            "qr_code": new_qr_code,
            "qr_payload": new_payload,
            "renewed_at": now,
            "updated_at": now,
        })

        return TicketResponse(
            ticket_id=ticket_id,
            booking_id=ticket["booking_id"],
            visitor_id=ticket["visitor_id"],
            visitor_name=ticket["visitor_name"],
            qr_code=new_qr_code,
            qr_payload=new_payload,
            validated=bool(ticket["validated"]),
            validated_at=ticket.get("validated_at"),
        )
