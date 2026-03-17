from datetime import datetime

from pydantic import BaseModel


class TicketResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_id: str
    visitor_name: str
    qr_code: str
    qr_payload: str
    validated: bool
    validated_at: datetime | None = None


class TicketValidationResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_id: str
    visitor_name: str
    validated: bool
    validated_at: datetime
