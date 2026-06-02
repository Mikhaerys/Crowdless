from datetime import date, datetime

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


class AttendanceHistoryResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_name: str
    ticket_type: str
    validated: bool
    validated_at: datetime


class CurrentVisitorsResponse(BaseModel):
    current_visitors: int


class PredictionItem(BaseModel):
    date: date
    day_name: str
    prediction: int
    factors: list[str]
    is_holiday: bool


class PredictionResponse(BaseModel):
    target_date: date
    days: int
    model_loaded: bool
    metadata: dict = Field(default_factory=dict)
    forecast: list[PredictionItem]

