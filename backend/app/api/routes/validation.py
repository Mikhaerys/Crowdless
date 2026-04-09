from fastapi import APIRouter, HTTPException, status

from app.models.ticket import QRValidationRequest, TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service


router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/tickets/{ticket_id}", response_model=TicketValidationResponse)
def validate_ticket(ticket_id: str) -> TicketValidationResponse:
    return ticket_service.validate_ticket(ticket_id)


@router.post("/qr", response_model=TicketValidationResponse)
def validate_qr_payload(payload: QRValidationRequest) -> TicketValidationResponse:
    # pyright: ignore[reportAttributeAccessIssue]
    validator = getattr(ticket_service, "validate_ticket_by_qr", None)
    if validator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QR validation service is unavailable",
        )
    return validator(payload.qr_payload)


@router.post("/tickets/{ticket_id}/renew", response_model=TicketResponse)
def renew_ticket_qr(ticket_id: str) -> TicketResponse:
    return ticket_service.renew_ticket_qr(ticket_id)
