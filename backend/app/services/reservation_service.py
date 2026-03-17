from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from app.core.config import settings
from app.models.booking import BookingCreate, BookingDetailsResponse, BookingResponse
from app.models.slot import TimeSlotCreate, TimeSlotResponse
from app.services.firestore_service import FirestoreService


class ReservationService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def list_slots(self, visit_date: date) -> list[TimeSlotResponse]:
        query = (
            self.firestore.time_slots.where(
                filter=FieldFilter("date", "==", visit_date.isoformat()))
            .order_by("start_time")
        )
        slots = []
        for document in query.stream():
            slot = document.to_dict()
            booked = int(slot.get("booked", 0))
            capacity = int(slot.get("capacity", 0))
            slots.append(
                TimeSlotResponse(
                    slot_id=document.id,
                    visit_date=visit_date,
                    start_time=datetime.strptime(
                        slot["start_time"], "%H:%M").time(),
                    end_time=datetime.strptime(
                        slot["end_time"], "%H:%M").time(),
                    capacity=capacity,
                    booked=booked,
                    available=max(capacity - booked, 0),
                )
            )
        return slots

    def create_slot(self, payload: TimeSlotCreate) -> TimeSlotResponse:
        slot_id = f"{payload.visit_date.isoformat()}_{payload.start_time.strftime('%H%M')}_{payload.end_time.strftime('%H%M')}"
        document = self.firestore.time_slots.document(slot_id)
        if document.get().exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Time slot already exists")

        document.set(
            {
                "date": payload.visit_date.isoformat(),
                "start_time": payload.start_time.strftime("%H:%M"),
                "end_time": payload.end_time.strftime("%H:%M"),
                "capacity": payload.capacity,
                "booked": 0,
            }
        )
        return TimeSlotResponse(
            slot_id=slot_id,
            visit_date=payload.visit_date,
            start_time=payload.start_time,
            end_time=payload.end_time,
            capacity=payload.capacity,
            booked=0,
            available=payload.capacity,
        )

    def create_booking(self, payload: BookingCreate) -> BookingResponse:
        total_tickets = payload.adults + payload.children
        slot_reference = self.firestore.time_slots.document(payload.slot_id)
        booking_reference = self.firestore.bookings.document()
        transaction = self.firestore.client.transaction()
        now = self.firestore.now()

        @firestore.transactional
        def reserve_slot(transaction: firestore.Transaction):
            slot_snapshot = slot_reference.get(transaction=transaction)
            if not slot_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Time slot not found")

            slot = slot_snapshot.to_dict()
            booked = int(slot.get("booked", 0))
            capacity = int(slot.get("capacity", 0))
            remaining = capacity - booked
            if remaining < total_tickets:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Time slot capacity exceeded")

            amount = round(
                payload.adults * settings.adult_ticket_price +
                payload.children * settings.child_ticket_price,
                2,
            )
            booking_data = {
                "slot_id": payload.slot_id,
                "visit_date": slot["date"],
                "adults": payload.adults,
                "children": payload.children,
                "total_tickets": total_tickets,
                "payment_status": "pending",
                "reservation_status": "reserved",
                "visitors_registered": 0,
                "tickets_created": 0,
                "amount": amount,
                "currency": payload.currency or settings.default_currency,
                "payment_id": None,
                "created_at": now,
                "updated_at": now,
            }
            transaction.update(
                slot_reference, {"booked": booked + total_tickets})
            transaction.set(booking_reference, booking_data)
            return booking_data

        booking_data = reserve_slot(transaction)
        return self._build_booking_response(booking_reference.id, booking_data)

    def get_booking(self, booking_id: str) -> BookingDetailsResponse:
        booking_snapshot = self.firestore.bookings.document(booking_id).get()
        if not booking_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        booking = booking_snapshot.to_dict()
        visitors = list(
            self.firestore.visitors.where(filter=FieldFilter(
                "booking_id", "==", booking_id)).stream()
        )
        tickets = list(self.firestore.tickets.where(
            filter=FieldFilter("booking_id", "==", booking_id)).stream())
        response = self._build_booking_response(booking_id, booking)
        return BookingDetailsResponse(
            **response.model_dump(),
            visitor_ids=[document.id for document in visitors],
            ticket_ids=[document.id for document in tickets],
        )

    def release_capacity(self, booking_id: str) -> BookingResponse:
        booking_reference = self.firestore.bookings.document(booking_id)
        transaction = self.firestore.client.transaction()
        now = self.firestore.now()

        @firestore.transactional
        def rollback_reservation(transaction: firestore.Transaction):
            booking_snapshot = booking_reference.get(transaction=transaction)
            if not booking_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

            booking = booking_snapshot.to_dict()
            if booking.get("reservation_status") == "released":
                return booking

            slot_reference = self.firestore.time_slots.document(
                booking["slot_id"])
            slot_snapshot = slot_reference.get(transaction=transaction)
            if not slot_snapshot.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Time slot not found")

            slot = slot_snapshot.to_dict()
            new_booked = max(int(slot.get("booked", 0)) -
                             int(booking.get("total_tickets", 0)), 0)
            booking["reservation_status"] = "released"
            booking["updated_at"] = now
            transaction.update(slot_reference, {"booked": new_booked})
            transaction.update(
                booking_reference,
                {"reservation_status": "released", "updated_at": now},
            )
            return booking

        booking = rollback_reservation(transaction)
        return self._build_booking_response(booking_id, booking)

    def _build_booking_response(self, booking_id: str, booking: dict) -> BookingResponse:
        return BookingResponse(
            booking_id=booking_id,
            slot_id=booking["slot_id"],
            visit_date=date.fromisoformat(booking["visit_date"]),
            adults=int(booking["adults"]),
            children=int(booking["children"]),
            total_tickets=int(booking["total_tickets"]),
            payment_status=booking["payment_status"],
            reservation_status=booking["reservation_status"],
            visitors_registered=int(booking.get("visitors_registered", 0)),
            tickets_created=int(booking.get("tickets_created", 0)),
            amount=float(booking["amount"]),
            currency=booking["currency"],
            payment_id=booking.get("payment_id"),
            created_at=booking["created_at"],
            updated_at=booking["updated_at"],
        )
