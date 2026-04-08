from fastapi import APIRouter
from app.models.ticket import TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/tickets/{ticket_id}", response_model=TicketValidationResponse)
def validate_ticket(ticket_id: str) -> TicketValidationResponse:
    """Valida un ticket en la entrada del museo. Solo puede usarse una vez."""
    return ticket_service.validate_ticket(ticket_id)


@router.post("/tickets/{ticket_id}/renew", response_model=TicketResponse)
def renew_ticket_qr(ticket_id: str) -> TicketResponse:
    """
    Renueva el QR de un ticket no validado.
    Usado por el museo cuando un visitante reporta pérdida o fraude.
    El QR anterior queda inválido automáticamente.
    """
    return ticket_service.renew_ticket_qr(ticket_id)