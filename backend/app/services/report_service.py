from __future__ import annotations
import matplotlib.pyplot as plt

from datetime import date
from io import BytesIO

import matplotlib
import pandas as pd
from google.cloud.firestore_v1 import FieldFilter

from app.models.report import ReportSummaryResponse
from app.services.firestore_service import FirestoreService


matplotlib.use("Agg")


class ReportService:
    def __init__(self, firestore_service: FirestoreService) -> None:
        self.firestore = firestore_service

    def _get_booking_rows(self, start_date: date, end_date: date) -> list[dict[str, str | int | float]]:
        bookings_query = (
            self.firestore.bookings.where(filter=FieldFilter(
                "visit_date", ">=", start_date.isoformat()))
            .where(filter=FieldFilter("visit_date", "<=", end_date.isoformat()))
        )
        rows: list[dict[str, str | int | float]] = []
        for document in bookings_query.stream():
            booking = document.to_dict()
            rows.append(
                {
                    "booking_id": document.id,
                    "slot_id": booking["slot_id"],
                    "visit_date": booking["visit_date"],
                    "total_tickets": int(booking["total_tickets"]),
                    "amount": float(booking["amount"]),
                    "payment_status": booking["payment_status"],
                }
            )
        return rows

    def get_summary(self, start_date: date, end_date: date) -> ReportSummaryResponse:
        rows = self._get_booking_rows(start_date, end_date)

        if not rows:
            return ReportSummaryResponse(
                start_date=start_date,
                end_date=end_date,
                total_bookings=0,
                total_tickets=0,
                approved_revenue=0.0,
                payment_breakdown={},
                daily_bookings={},
                slot_ticket_distribution={},
            )

        data_frame = pd.DataFrame(rows)
        approved_rows = data_frame[data_frame["payment_status"] == "approved"]
        return ReportSummaryResponse(
            start_date=start_date,
            end_date=end_date,
            total_bookings=int(len(data_frame.index)),
            total_tickets=int(data_frame["total_tickets"].sum()),
            approved_revenue=float(round(approved_rows["amount"].sum(), 2)),
            payment_breakdown={key: int(
                value) for key, value in data_frame["payment_status"].value_counts().items()},
            daily_bookings={key: int(value) for key, value in data_frame.groupby(
                "visit_date")["booking_id"].count().items()},
            slot_ticket_distribution={
                key: int(value) for key, value in data_frame.groupby("slot_id")["total_tickets"].sum().items()
            },
        )

    def export_bookings_csv(self, start_date: date, end_date: date) -> bytes:
        data_frame = pd.DataFrame(self._get_booking_rows(start_date, end_date))
        if data_frame.empty:
            data_frame = pd.DataFrame(
                columns=["booking_id", "slot_id", "visit_date",
                         "total_tickets", "amount", "payment_status"]
            )
        return data_frame.to_csv(index=False).encode("utf-8")

    def get_occupancy_chart(self, start_date: date, end_date: date) -> bytes:
        slots_query = (
            self.firestore.time_slots.where(
                filter=FieldFilter("date", ">=", start_date.isoformat()))
            .where(filter=FieldFilter("date", "<=", end_date.isoformat()))
            .order_by("date")
            .order_by("start_time")
        )
        rows = []
        for document in slots_query.stream():
            slot = document.to_dict()
            rows.append(
                {
                    "label": f"{slot['date']} {slot['start_time']}",
                    "booked": int(slot.get("booked", 0)),
                    "capacity": int(slot.get("capacity", 0)),
                }
            )

        if not rows:
            figure, axis = plt.subplots(figsize=(8, 4))
            axis.text(0.5, 0.5, "No occupancy data", ha="center", va="center")
            axis.axis("off")
        else:
            data_frame = pd.DataFrame(rows)
            figure, axis = plt.subplots(figsize=(10, 5))
            positions = range(len(data_frame.index))
            axis.bar(positions, data_frame["capacity"],
                     label="Capacity", color="#d9d9d9")
            axis.bar(positions, data_frame["booked"],
                     label="Booked", color="#1f77b4")
            axis.set_xticks(list(positions))
            axis.set_xticklabels(data_frame["label"], rotation=45, ha="right")
            axis.set_ylabel("Visitors")
            axis.set_title("Museum Slot Occupancy")
            axis.legend()
            figure.tight_layout()

        buffer = BytesIO()
        figure.savefig(buffer, format="png", bbox_inches="tight")
        plt.close(figure)
        return buffer.getvalue()
