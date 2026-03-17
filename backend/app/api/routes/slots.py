from datetime import date

from fastapi import APIRouter, Query, status

from app.models.slot import TimeSlotCreate, TimeSlotResponse
from app.services.runtime import reservation_service


router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("", response_model=list[TimeSlotResponse])
def list_time_slots(visit_date: date = Query(...)) -> list[TimeSlotResponse]:
    return reservation_service.list_slots(visit_date)


@router.post("", response_model=TimeSlotResponse, status_code=status.HTTP_201_CREATED)
def create_time_slot(payload: TimeSlotCreate) -> TimeSlotResponse:
    return reservation_service.create_slot(payload)
