from datetime import date, time

from pydantic import BaseModel, Field


class TimeSlotCreate(BaseModel):
    visit_date: date
    start_time: time
    end_time: time
    capacity: int = Field(gt=0, le=15)


class TimeSlotResponse(BaseModel):
    slot_id: str
    visit_date: date
    start_time: time
    end_time: time
    capacity: int
    booked: int
    available: int
