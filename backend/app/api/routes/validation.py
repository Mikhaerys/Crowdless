from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
import math
import re
import unicodedata

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore
import base64
import requests

from app.models.ticket import QRValidationRequest, TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service
from app.core.config import settings
from app.core.auth import (
    hash_password,
    verify_credentials,
    create_session,
    require_admin,
    require_guard_or_admin,
    get_current_user_role,
    update_password,
)

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

        # Codificar la imagen directamente en memoria (Base64)
        encoded_image = base64.b64encode(contents).decode("utf-8")

        # Ejecutar modelo vía HTTP POST
        payload = {
            "api_key": settings.roboflow_api_key,
            "inputs": {
                "image": {
                    "type": "base64",
                    "value": encoded_image
                }
            }
        }

        response = requests.post(
            settings.roboflow_api_url,
            json=payload,
            timeout=25.0  # Límite de 55 segundos en la petición externa
        )
        response.raise_for_status()
        res_data = response.json()

        # Determinar si existe una Cédula
        is_cedula = False
        if isinstance(res_data, dict) and "outputs" in res_data:
            outputs = res_data["outputs"]
            result_dict = outputs[0] if isinstance(outputs, list) and len(outputs) > 0 else {}
        elif isinstance(res_data, list) and len(res_data) > 0:
            result_dict = res_data[0]
        elif isinstance(res_data, dict):
            result_dict = res_data
        else:
            result_dict = {}

        predictions = result_dict.get("predictions", {}).get("predictions", []) if isinstance(result_dict, dict) else []
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

        ocr_text = str(result_dict.get("Text", "") or "") if isinstance(result_dict, dict) else ""

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
def validate_ticket(ticket_id: str, role: str = Depends(require_guard_or_admin)) -> TicketValidationResponse:
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
def renew_ticket_qr(ticket_id: str, role: str = Depends(require_admin)) -> TicketResponse:
    """
    Renueva el QR de un ticket no validado.
    Usado por el museo cuando un visitante reporta pérdida o fraude.
    El QR anterior queda inválido automáticamente.
    """
    return ticket_service.renew_ticket_qr(ticket_id)


# ── Guard Verification Flows ─────────────────────────────

class GuardLoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class GuardQRVerificationRequest(BaseModel):
    qr_payload: str


class GuardQRVerificationResponse(BaseModel):
    ticket_id: str
    booking_id: str
    visitor_id: str
    visitor_name: str
    id_number: str
    birth_date: str
    ticket_type: str
    visit_date: str
    slot_id: str
    slot_start_time: str
    slot_end_time: str


@router.post("/guard/login")
def guard_login(payload: GuardLoginRequest):
    if verify_credentials("guard", payload.username, payload.password):
        token = create_session("guard", payload.username)
        return {"success": True, "token": token, "message": "Inicio de sesión exitoso"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos",
    )


@router.post("/admin/login")
def admin_login(payload: GuardLoginRequest):
    if verify_credentials("admin", payload.username, payload.password):
        token = create_session("admin", payload.username)
        return {"success": True, "token": token, "message": "Inicio de sesión exitoso"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos",
    )


@router.post("/change-password")
def change_password(payload: PasswordChangeRequest, role: str = Depends(get_current_user_role)):
    # Verify old password
    doc_ref = ticket_service.firestore.client.collection("credentials").document(role)
    doc_snap = doc_ref.get()
    if not doc_snap.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciales no inicializadas en la base de datos"
        )
    creds = doc_snap.to_dict()
    if creds.get("password_hash") != hash_password(payload.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    update_password(role, payload.new_password)
    return {"success": True, "message": "Contraseña cambiada exitosamente"}


@router.post("/guard/verify-qr", response_model=GuardQRVerificationResponse)
def guard_verify_qr(payload: GuardQRVerificationRequest, role: str = Depends(require_guard_or_admin)):
    # Parse QR payload to get ticket_id
    try:
        ticket_id = ticket_service.get_ticket_id_from_qr_payload(payload.qr_payload)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Código QR inválido: {str(error)}",
        )

    # Load ticket
    ticket_reference = ticket_service.firestore.tickets.document(ticket_id)
    ticket_snapshot = ticket_reference.get()
    if not ticket_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tiquete no encontrado en el sistema",
        )
    ticket = ticket_snapshot.to_dict()

    # Check if validated
    if ticket.get("validated"):
        validated_at = ticket.get("validated_at")
        validated_at_text = (
            validated_at.isoformat() if hasattr(validated_at, "isoformat") else str(validated_at)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El tiquete ya fue validado en la entrada a las {validated_at_text}",
        )

    # Load booking
    booking_id = ticket.get("booking_id")
    booking_reference = ticket_service.firestore.bookings.document(booking_id)
    booking_snapshot = booking_reference.get()
    if not booking_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva asociada al tiquete no encontrada",
        )
    booking = booking_snapshot.to_dict()

    # Check booking status
    if booking.get("payment_status") != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pago de la reserva no ha sido aprobado",
        )
    if booking.get("reservation_status") != "reserved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La reserva no está activa o fue cancelada",
        )

    # Load visitor info
    visitor_id = ticket.get("visitor_id")
    visitor_reference = ticket_service.firestore.visitors.document(visitor_id)
    visitor_snapshot = visitor_reference.get()
    if not visitor_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Información del visitante no encontrada",
        )
    visitor = visitor_snapshot.to_dict()

    # Get time slot
    slot_id = booking.get("slot_id")
    slot_reference = ticket_service.firestore.time_slots.document(slot_id)
    slot_snapshot = slot_reference.get()
    if not slot_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Franja horaria no encontrada",
        )
    slot = slot_snapshot.to_dict()

    # Validate slot (date and time) in Colombia timezone
    utc_now = ticket_service.firestore.now()
    colombia_now = utc_now - timedelta(hours=5)
    current_date_str = colombia_now.date().isoformat()
    current_time_str = colombia_now.strftime("%H:%M")

    # Date check
    visit_date = booking.get("visit_date")
    if visit_date != current_date_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fecha incorrecta. El tiquete es para el {visit_date}, pero hoy es {current_date_str}",
        )

    # Time check (Current slot or next slot)
    slots_query = ticket_service.firestore.time_slots.where(
        filter=FieldFilter("date", "==", current_date_str)
    ).stream()
    day_slots = []
    for doc in slots_query:
        s = doc.to_dict()
        s["id"] = doc.id
        day_slots.append(s)
    
    # Sort slots by start_time
    day_slots.sort(key=lambda x: x.get("start_time", ""))

    # Determine current slot and next slot
    current_slot_id = None
    next_slot_id = None

    # Check for current slot
    for s in day_slots:
        st = s.get("start_time", "")
        et = s.get("end_time", "")
        if st <= current_time_str <= et:
            current_slot_id = s["id"]
            break

    # Check for next slot
    for s in day_slots:
        st = s.get("start_time", "")
        if st > current_time_str:
            next_slot_id = s["id"]
            break

    # The ticket slot must match current_slot_id or next_slot_id
    if slot_id != current_slot_id and slot_id != next_slot_id:
        ticket_start = slot.get("start_time", "")
        ticket_end = slot.get("end_time", "")
        
        if ticket_end < current_time_str:
            time_error_detail = (
                f"Entrada denegada. Su franja horaria ({ticket_start} - {ticket_end}) ya expiró. "
                f"Hora actual: {current_time_str}."
            )
        else:
            time_error_detail = (
                f"Entrada denegada. Su franja horaria es {ticket_start} - {ticket_end}, "
                f"pero aún es temprano para ingresar. Hora actual: {current_time_str}."
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=time_error_detail,
        )

    return GuardQRVerificationResponse(
        ticket_id=ticket_id,
        booking_id=booking_id,
        visitor_id=visitor_id,
        visitor_name=visitor.get("name", ""),
        id_number=visitor.get("id_number", ""),
        birth_date=visitor.get("birth_date", ""),
        ticket_type=ticket.get("ticket_type", "adult"),
        visit_date=visit_date,
        slot_id=slot_id,
        slot_start_time=slot.get("start_time", ""),
        slot_end_time=slot.get("end_time", ""),
    )


@router.post("/guard/verify-identity")
async def guard_verify_identity(request: Request, role: str = Depends(require_guard_or_admin)):
    """
    Valida la imagen de la cédula mediante Roboflow, compara los datos con los del visitante.
    Si coincide, marca el tiquete como validado (validated=True, validated_at=now) y confirma.
    Si no coincide, no lo marca y devuelve el error detallado de la discrepancia.
    """
    try:
        # Extract image (multipart form or raw bytes)
        content_type = request.headers.get("content-type", "")
        form_data = None
        if "multipart/form-data" in content_type:
            form_data = await request.form()
            file_obj = form_data.get("file")
            if file_obj is None:
                raise HTTPException(
                    status_code=400, detail="Falta el archivo de imagen de la cédula"
                )
            contents = await file_obj.read()
        else:
            contents = await request.body()

        if not contents:
            raise HTTPException(status_code=400, detail="El archivo está vacío")

        ticket_id = _extract_ticket_id(request, form_data)
        if not ticket_id:
            raise HTTPException(
                status_code=400, detail="Falta el ticket_id para la verificación"
            )

        # Encode image directly in memory (Base64)
        encoded_image = base64.b64encode(contents).decode("utf-8")

        # Roboflow inference API
        payload = {
            "api_key": settings.roboflow_api_key,
            "inputs": {
                "image": {
                    "type": "base64",
                    "value": encoded_image
                }
            }
        }

        # Send query to Roboflow
        response = requests.post(
            settings.roboflow_api_url,
            json=payload,
            timeout=25.0
        )
        response.raise_for_status()
        res_data = response.json()

        # Check if ID card detected
        is_cedula = False
        if isinstance(res_data, dict) and "outputs" in res_data:
            outputs = res_data["outputs"]
            result_dict = outputs[0] if isinstance(outputs, list) and len(outputs) > 0 else {}
        elif isinstance(res_data, list) and len(res_data) > 0:
            result_dict = res_data[0]
        elif isinstance(res_data, dict):
            result_dict = res_data
        else:
            result_dict = {}

        predictions = result_dict.get("predictions", {}).get("predictions", []) if isinstance(result_dict, dict) else []
        for pred in predictions:
            if pred.get("class") == "Cedula" and pred.get("confidence", 0) >= _ID_CARD_CONFIDENCE_THRESHOLD:
                is_cedula = True
                break

        if not is_cedula:
            return {
                "valid": False,
                "is_cedula": False,
                "detail": "No se detectó un documento de identidad (cédula) válido en la imagen.",
                "identity_match": None,
            }

        ocr_text = str(result_dict.get("Text", "") or "") if isinstance(result_dict, dict) else ""

        # Compare with ticket owner data
        ticket_owner = _load_ticket_owner(ticket_id)
        name_ok = _name_matches(ocr_text, str(ticket_owner["visitor_name"]))
        id_ok = _id_number_matches(ocr_text, str(ticket_owner["id_number"]))
        birth_ok = _birth_date_matches(ocr_text, ticket_owner["birth_date"])

        identity_ok = name_ok and id_ok and birth_ok

        if not identity_ok:
            reasons = []
            if not name_ok:
                reasons.append(f"El nombre '{ticket_owner['visitor_name']}' no coincide.")
            if not id_ok:
                reasons.append(f"El número de cédula '{ticket_owner['id_number']}' no coincide.")
            if not birth_ok:
                reasons.append(f"La fecha de nacimiento no coincide.")

            return {
                "valid": False,
                "is_cedula": True,
                "detail": "Verificación de identidad fallida: " + " ".join(reasons),
                "identity_match": {
                    "ticket_id": ticket_id,
                    "name": name_ok,
                    "id_number": id_ok,
                    "birth_date": birth_ok,
                },
            }

        # If identity is ok, validate the ticket in database transactionally
        ticket_ref = ticket_service.firestore.tickets.document(ticket_id)
        transaction = ticket_service.firestore.client.transaction()
        now = ticket_service.firestore.now()

        @firestore.transactional
        def validate(trans: firestore.Transaction):
            ticket_snap = ticket_ref.get(transaction=trans)
            if not ticket_snap.exists:
                raise HTTPException(status_code=404, detail="Ticket not found")
            tick = ticket_snap.to_dict()
            if tick.get("validated"):
                raise HTTPException(status_code=409, detail="Ticket already validated")
            
            trans.update(ticket_ref, {"validated": True, "validated_at": now})
            return tick

        validate(transaction)

        return {
            "valid": True,
            "is_cedula": True,
            "detail": "Entrada autorizada correctamente. Identidad verificada con éxito.",
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
