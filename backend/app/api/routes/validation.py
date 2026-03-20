from fastapi import APIRouter

from app.models.ticket import TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service


router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/tickets/{ticket_id}", response_model=TicketValidationResponse)
def validate_ticket(ticket_id: str) -> TicketValidationResponse:
    return ticket_service.validate_ticket(ticket_id)


@router.post("/tickets/{ticket_id}/renew", response_model=TicketResponse)
def renew_ticket_qr(ticket_id: str) -> TicketResponse:
    return ticket_service.renew_ticket_qr(ticket_id)
