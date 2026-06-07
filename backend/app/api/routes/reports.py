from datetime import date

from fastapi import APIRouter, Query, Depends
from fastapi.responses import Response

from app.models.report import ReportSummaryResponse, AttendanceHistoryResponse, CurrentVisitorsResponse, PredictionResponse
from app.services.runtime import report_service, prediction_service
from app.core.auth import require_admin


router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/summary", response_model=ReportSummaryResponse)
def get_summary_report(start_date: date = Query(...), end_date: date = Query(...)) -> ReportSummaryResponse:
    return report_service.get_summary(start_date, end_date)


@router.get("/bookings.csv")
def export_bookings_csv(start_date: date = Query(...), end_date: date = Query(...)) -> Response:
    report = report_service.export_bookings_csv(start_date, end_date)
    return Response(
        content=report,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bookings-report.csv"},
    )


@router.get("/occupancy-chart")
def get_occupancy_chart(start_date: date = Query(...), end_date: date = Query(...)) -> Response:
    chart = report_service.get_occupancy_chart(start_date, end_date)
    return Response(content=chart, media_type="image/png")


@router.get("/attendance-history", response_model=list[AttendanceHistoryResponse])
def get_attendance_history(limit: int = Query(100)) -> list[AttendanceHistoryResponse]:
    return report_service.get_attendance_history(limit)


@router.get("/current-visitors", response_model=CurrentVisitorsResponse)
def get_current_visitors() -> CurrentVisitorsResponse:
    count = report_service.get_current_visitors()
    return CurrentVisitorsResponse(current_visitors=count)


@router.get("/predict-attendance", response_model=PredictionResponse)
def predict_attendance(
    target_date: date = Query(...),
    days: int = Query(7)
) -> PredictionResponse:
    forecast = prediction_service.forecast_range(target_date, days)
    return PredictionResponse(
        target_date=target_date,
        days=days,
        model_loaded=prediction_service.model_loaded,
        metadata=prediction_service.metadata,
        forecast=forecast
    )


@router.post("/predict-attendance/reload")
def reload_prediction_model() -> dict[str, str | bool]:
    success = prediction_service.reload_model()
    return {
        "status": "success" if success else "failed",
        "model_loaded": success
    }

