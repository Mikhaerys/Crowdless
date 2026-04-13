from fastapi import APIRouter, HTTPException, status, Request
import tempfile
import os
import base64
import requests

from app.models.ticket import QRValidationRequest, TicketResponse, TicketValidationResponse
from app.services.runtime import ticket_service
from app.core.config import settings

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/id-card")
async def validate_id_card(request: Request):
    """Valida una imagen para detectar si es una cédula colombiana"""
    try:
        # Extraer imagen (ya sea como multipart form o como raw bytes)
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            form = await request.form()
            file_obj = form.get("file")
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
                if pred.get("class") == "Cedula" and pred.get("confidence", 0) > 0.5:
                    is_cedula = True
                    break

        return {"valid": is_cedula}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
