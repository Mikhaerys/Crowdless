from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TicketResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_id: str
    visitor_name: str
    ticket_type: Literal["adult", "child"]
    qr_code: str
    qr_payload: str
    validated: bool
    validated_at: datetime | None = None


class TicketValidationResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_id: str
    visitor_name: str
    ticket_type: Literal["adult", "child"]
    validated: bool
    validated_at: datetime


class QRValidationRequest(BaseModel):
    qr_payload: str
