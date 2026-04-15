from datetime import date
from difflib import SequenceMatcher
import math
import re
import unicodedata

from fastapi import APIRouter, HTTPException, status, Request
import tempfile
import os
import base64
import requests

from app.models.ticket import QRValidationRequest, TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service
from app.core.config import settings

router = APIRouter(prefix="/validation", tags=["validation"])

_ID_CARD_CONFIDENCE_THRESHOLD = 0.35
_MONTH_ABBREVIATIONS: dict[int, tuple[str, ...]] = {
    1: ("ENE",),
    2: ("FEB",),
    3: ("MAR",),
    4: ("ABR",),
    5: ("MAY",),
    6: ("JUN",),
    7: ("JUL",),
    8: ("AGO",),
    9: ("SEP", "SEPT"),
    10: ("OCT",),
    11: ("NOV",),
    12: ("DIC",),
}


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value)


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _name_matches(ocr_text: str, expected_name: str) -> bool:
    normalized_ocr = _normalize_text(ocr_text)
    normalized_name = _normalize_text(expected_name)
    if not normalized_ocr or not normalized_name:
        return False
    if normalized_name in normalized_ocr:
        return True

    ocr_tokens = [token for token in normalized_ocr.split(
        " ") if len(token) >= 2]
    expected_tokens = [
        token for token in normalized_name.split(" ") if len(token) >= 3
    ]
    if not ocr_tokens or not expected_tokens:
        return False

    matches = 0
    for expected_token in expected_tokens:
        best = max((_ratio(expected_token, token)
                   for token in ocr_tokens), default=0.0)
        if best >= 0.76:
            matches += 1

    required_matches = max(1, math.ceil(len(expected_tokens) * 0.6))
    return matches >= required_matches


def _id_number_matches(ocr_text: str, expected_id_number: str) -> bool:
    expected_digits = _digits_only(expected_id_number)
    ocr_digits = _digits_only(ocr_text)
    if not expected_digits or not ocr_digits:
        return False
    if expected_digits in ocr_digits:
        return True

    expected_length = len(expected_digits)
    best_similarity = 0.0
    for window_size in range(max(1, expected_length - 1), expected_length + 2):
        if window_size > len(ocr_digits):
            continue
        for start in range(0, len(ocr_digits) - window_size + 1):
            candidate = ocr_digits[start:start + window_size]
            best_similarity = max(
                best_similarity, _ratio(expected_digits, candidate))
            if best_similarity >= 0.9:
                return True

    return False


def _birth_date_matches(ocr_text: str, expected_birth_date: date) -> bool:
    normalized_ocr = _normalize_text(ocr_text)
    if not normalized_ocr:
        return False

    day = expected_birth_date.day
    month = expected_birth_date.month
    year = expected_birth_date.year
    month_options = _MONTH_ABBREVIATIONS.get(month, tuple())

    month_pattern = "|".join(month_options)
    if month_pattern:
        text_month_pattern = rf"\b0?{day}\s*(?:{month_pattern})\s*{year}\b"
        if re.search(text_month_pattern, normalized_ocr):
            return True

    numeric_patterns = [
        rf"\b0?{day}[\/\-\.\s]0?{month}[\/\-\.\s]{year}\b",
        rf"\b{year}[\/\-\.\s]0?{month}[\/\-\.\s]0?{day}\b",
    ]
    for pattern in numeric_patterns:
        if re.search(pattern, normalized_ocr):
            return True

    tokens = normalized_ocr.split(" ")
    has_year = str(year) in tokens
    has_day = str(day) in tokens or f"0{day}" in tokens
    has_month = any(
        any(_ratio(month_candidate, token) >=
            0.75 for month_candidate in month_options)
        for token in tokens
        if len(token) <= 5
    )
    return has_year and has_day and has_month


def _extract_ticket_id(request: Request, form_data) -> str | None:
    ticket_id_from_query = request.query_params.get("ticket_id")
    if ticket_id_from_query:
        return ticket_id_from_query.strip()

    ticket_id_from_header = request.headers.get("x-ticket-id")
    if ticket_id_from_header:
        return ticket_id_from_header.strip()

    if form_data is not None:
        ticket_id_from_form = form_data.get("ticket_id")
        if isinstance(ticket_id_from_form, str) and ticket_id_from_form.strip():
            return ticket_id_from_form.strip()

    qr_payload = request.query_params.get(
        "qr_payload") or request.headers.get("x-qr-payload")
    if not qr_payload and form_data is not None:
        raw_qr_payload = form_data.get("qr_payload")
        if isinstance(raw_qr_payload, str):
            qr_payload = raw_qr_payload

    if qr_payload:
        try:
            # Reuse existing QR parser to support signed and legacy payloads.
            # pyright: ignore[reportPrivateUsage]
            return ticket_service.get_ticket_id_from_qr_payload(qr_payload)
        except HTTPException:
            return None

    return None


def _load_ticket_owner(ticket_id: str) -> dict:
    ticket_reference = ticket_service.firestore.tickets.document(ticket_id)
    ticket_snapshot = ticket_reference.get()
    if not ticket_snapshot.exists:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket = ticket_snapshot.to_dict()
    visitor_id = ticket.get("visitor_id")
    if not visitor_id:
        raise HTTPException(
            status_code=409,
            detail="Ticket is missing visitor association",
        )

    visitor_reference = ticket_service.firestore.visitors.document(visitor_id)
    visitor_snapshot = visitor_reference.get()
    if not visitor_snapshot.exists:
        raise HTTPException(status_code=404, detail="Visitor not found")

    visitor = visitor_snapshot.to_dict()
    birth_date_raw = visitor.get("birth_date")
    if not isinstance(birth_date_raw, str):
        raise HTTPException(
            status_code=409, detail="Visitor birth date is invalid")

    try:
        birth_date_value = date.fromisoformat(birth_date_raw)
    except ValueError as error:
        raise HTTPException(
            status_code=409, detail="Visitor birth date is invalid") from error

    return {
        "visitor_name": visitor.get("name", ""),
        "id_number": visitor.get("id_number", ""),
        "birth_date": birth_date_value,
    }


@router.post("/id-card")
async def validate_id_card(request: Request):
    """Valida una imagen de cédula y, si se recibe ticket, valida identidad del titular."""
    try:
        # Extraer imagen (ya sea como multipart form o como raw bytes)
        content_type = request.headers.get("content-type", "")
        form_data = None
        if "multipart/form-data" in content_type:
            form_data = await request.form()
            file_obj = form_data.get("file")
            if file_obj is None:
                raise HTTPException(
                    status_code=400, detail="Missing multipart file field")
            contents = await file_obj.read()
        else:
            contents = await request.body()

        if not contents:
            raise HTTPException(status_code=400, detail="Empty file contents")

        # Guardar la imagen en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Leer y codificar la imagen en base64
        with open(tmp_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Ejecutar modelo vía HTTP POST
        payload = {
            "inputs": {
                "image": {
                    "type": "base64",
                    "value": encoded_image
                }
            }
        }

        response = requests.post(
            settings.roboflow_api_url,
            params={"api_key": settings.roboflow_api_key},
            json=payload,
            timeout=25.0  # Límite de 55 segundos en la petición externa
        )
        response.raise_for_status()

        result = [response.json()]
        # Eliminar archivo temporal
        os.remove(tmp_path)

        # Determinar si existe una Cédula
        is_cedula = False
        if isinstance(result, list) and len(result) > 0:
            predictions = result[0].get(
                "predictions", {}).get("predictions", [])
            for pred in predictions:
                if pred.get("class") == "Cedula" and pred.get("confidence", 0) >= _ID_CARD_CONFIDENCE_THRESHOLD:
                    is_cedula = True
                    break

        if not is_cedula:
            return {
                "valid": False,
                "is_cedula": False,
                "identity_match": None,
            }

        ocr_text = ""
        if isinstance(result[0], dict):
            ocr_text = str(result[0].get("Text", "") or "")

        ticket_id = _extract_ticket_id(request, form_data)
        if not ticket_id:
            return {
                "valid": True,
                "is_cedula": True,
                "identity_match": None,
            }

        ticket_owner = _load_ticket_owner(ticket_id)

        name_ok = _name_matches(ocr_text, str(ticket_owner["visitor_name"]))
        id_ok = _id_number_matches(ocr_text, str(ticket_owner["id_number"]))
        birth_ok = _birth_date_matches(ocr_text, ticket_owner["birth_date"])

        identity_ok = name_ok and id_ok and birth_ok
        return {
            "valid": identity_ok,
            "is_cedula": True,
            "identity_match": {
                "ticket_id": ticket_id,
                "name": name_ok,
                "id_number": id_ok,
                "birth_date": birth_ok,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tickets/{ticket_id}", response_model=TicketValidationResponse)
def validate_ticket(ticket_id: str) -> TicketValidationResponse:
    """Valida un ticket en la entrada del museo. Solo puede usarse una vez."""
    return ticket_service.validate_ticket(ticket_id)


@router.post("/qr", response_model=TicketValidationResponse)
def validate_qr_payload(payload: QRValidationRequest) -> TicketValidationResponse:
    # pyright: ignore[reportAttributeAccessIssue]
    validator = getattr(ticket_service, "validate_ticket_by_qr", None)
    if validator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QR validation service is unavailable",
        )
    return validator(payload.qr_payload)


@router.post("/tickets/{ticket_id}/renew", response_model=TicketResponse)
def renew_ticket_qr(ticket_id: str) -> TicketResponse:
    """
    Renueva el QR de un ticket no validado.
    Usado por el museo cuando un visitante reporta pérdida o fraude.
    El QR anterior queda inválido automáticamente.
    """
    return ticket_service.renew_ticket_qr(ticket_id)
