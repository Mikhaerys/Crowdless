from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.models.report import ReportSummaryResponse
from app.services.runtime import report_service


router = APIRouter(prefix="/reports", tags=["reports"])


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
