from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class VisitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    birth_date: date
    id_number: str = Field(min_length=3, max_length=40)


class BookingCreate(BaseModel):
    slot_id: str = Field(min_length=3)
    adults: int = Field(ge=0, default=0)
    children: int = Field(ge=0, default=0)
    currency: str | None = None

    @field_validator("children")
    @classmethod
    def validate_total_tickets(cls, children: int, info):
        adults = info.data.get("adults", 0)
        if adults + children <= 0:
            raise ValueError("At least one ticket is required")
        return children


class BookingResponse(BaseModel):
    booking_id: str
    slot_id: str
    visit_date: date
    adults: int
    children: int
    total_tickets: int
    payment_status: str
    reservation_status: str
    visitors_registered: int
    tickets_created: int
    amount: float
    currency: str
    payment_id: str | None = None
    created_at: datetime
    updated_at: datetime


class BookingDetailsResponse(BookingResponse):
    visitor_ids: list[str] = Field(default_factory=list)
    ticket_ids: list[str] = Field(default_factory=list)


class VisitorRegistrationRequest(BaseModel):
    # Email del comprador — se usa para enviar todos los QRs
    contact_email: EmailStr
    visitors: list[VisitorCreate]


class PaymentVerificationRequest(BaseModel):
    status: Literal["approved", "failed", "cancelled"] = "approved"
    provider: str = Field(default="test")
    transaction_id: str | None = None


class PaymentResponse(BaseModel):
    payment_id: str
    booking_id: str
    provider: str
    transaction_id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    