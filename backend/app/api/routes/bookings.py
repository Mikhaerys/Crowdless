from fastapi import APIRouter, status

from app.models.booking import BookingCreate, BookingDetailsResponse, BookingResponse, VisitorRegistrationRequest
from app.models.ticket import TicketResponse
from app.services.runtime import reservation_service, ticket_service


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate) -> BookingResponse:
    return reservation_service.create_booking(payload)


@router.get("/{booking_id}", response_model=BookingDetailsResponse)
def get_booking(booking_id: str) -> BookingDetailsResponse:
    return reservation_service.get_booking(booking_id)


@router.post("/{booking_id}/visitors", response_model=list[TicketResponse], status_code=status.HTTP_201_CREATED)
def register_visitors(booking_id: str, payload: VisitorRegistrationRequest) -> list[TicketResponse]:
    return ticket_service.register_visitors(booking_id, payload)


@router.get("/{booking_id}/tickets", response_model=list[TicketResponse])
def get_booking_tickets(booking_id: str) -> list[TicketResponse]:
    return ticket_service.get_tickets_by_booking(booking_id)
