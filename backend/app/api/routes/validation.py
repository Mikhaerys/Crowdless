from fastapi import APIRouter

from app.models.ticket import TicketValidationResponse
from app.services.runtime import ticket_service


router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/tickets/{ticket_id}", response_model=TicketValidationResponse)
def validate_ticket(ticket_id: str) -> TicketValidationResponse:
    return ticket_service.validate_ticket(ticket_id)
