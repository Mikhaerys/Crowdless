from datetime import date

from pydantic import BaseModel, Field


class ReportSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_bookings: int
    total_tickets: int
    approved_revenue: float
    payment_breakdown: dict[str, int] = Field(default_factory=dict)
    daily_bookings: dict[str, int] = Field(default_factory=dict)
    slot_ticket_distribution: dict[str, int] = Field(default_factory=dict)
