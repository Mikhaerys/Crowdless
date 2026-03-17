from __future__ import annotations

from datetime import date, datetime, time
from functools import cached_property
from typing import Any

from google.cloud import firestore

from app.core.config import settings


class FirestoreService:
    def __init__(self) -> None:
        self._client_kwargs: dict[str, Any] = {}
        if settings.firestore_project_id:
            self._client_kwargs["project"] = settings.firestore_project_id

    @cached_property
    def client(self) -> firestore.Client:
        return firestore.Client(**self._client_kwargs)

    @property
    def time_slots(self):
        return self.client.collection("time_slots")

    @property
    def bookings(self):
        return self.client.collection("bookings")

    @property
    def visitors(self):
        return self.client.collection("visitors")

    @property
    def tickets(self):
        return self.client.collection("tickets")

    @property
    def payments(self):
        return self.client.collection("payments")

    def now(self) -> datetime:
        return datetime.utcnow()

    def normalize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat(timespec="minutes")
        if isinstance(value, list):
            return [self.normalize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self.normalize_value(item) for key, item in value.items()}
        return value

    def normalize_document(self, document_id: str, data: dict[str, Any]) -> dict[str, Any]:
        normalized = {key: self.normalize_value(
            value) for key, value in data.items()}
        normalized["id"] = document_id
        return normalized
