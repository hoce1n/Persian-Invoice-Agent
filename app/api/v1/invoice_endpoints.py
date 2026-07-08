import logging
import uuid
import base64
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse

from app.config.settings import get_settings
from app.core.errors import ErrorCode, api_error, mask_email
from app.core.messages import (
    STT_FALLBACK_MESSAGE,
    STT_RATE_LIMIT_FALLBACK_MESSAGE,
    STT_TIMEOUT_FALLBACK_MESSAGE,
)
from app.schemas.invoice_schemas import (
    InvoiceApprovalResponse,
    InvoiceProcessResponse,
    InvoiceRequest,
    ProcessingStatus,
)
from app.services.email_service import EmailService
from app.services.llm_service import LLMService, LLMServiceError
from app.services.pdf_service import PDFService
from app.services.stt_service import STTService, STTServiceError
from app.services.tts_service import TTSService, TTSServiceError

logger = logging.getLogger(__name__)

router = APIRouter()
_settings = get_settings()

_llm_service = LLMService()
_pdf_service = PDFService()
_email_service = EmailService()
_stt_service = STTService()
_tts_service = TTSService()

# In-memory store for invoices awaiting manager approval
_pending_invoices: dict[str, dict[str, Any]] = {}


@router.post(
    "/process-invoice-request",
    response_model=InvoiceProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process an invoice request from text or audio",
)
async def process_invoice_request(
    client_text: str | None = Form(
        default=None,
        description="Persian text describing the invoice request",
    ),
    client_email: str | None = Form(
        default=None,
        description="Client email for invoice delivery after manager approval",
    ),
    audio: UploadFile | None = File(
        default=None,
        description="Optional audio file (transcribed via Whisper)",
    ),
) -> InvoiceProcessResponse:
    """
    Extract invoice data from Persian text or voice, generate an invoice file,
    and send it to the manager for human-in-the-loop approval.
    """
    text_input, fallback_response = await _resolve_input_text(client_text, audio)
    if fallback_response is not None:
        return fallback_response
    resolved_client_email = client_email or _settings.default_client_email

    return _run_invoice_pipeline(text_input, resolved_client_email)


@router.post(
    "/process-invoice-request/json",
    response_model=InvoiceProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process an invoice request from JSON body",
    include_in_schema=True,
)
async def process_invoice_request_json(
    request: InvoiceRequest,
) -> InvoiceProcessResponse:
    """JSON variant of the invoice processing endpoint for programmatic clients."""
    client_email = request.client_email or _settings.default_client_email
    return _run_invoice_pipeline(request.client_text or "", client_email)


@router.get(
    "/invoices/approve/{invoice_id}",
    response_model=InvoiceApprovalResponse,
    summary="Manager approves a pending invoice",
    responses={200: {"description": "Approval successful (JSON or HTML)"}},
)
async def approve_invoice(
    invoice_id: str,
    request: Request,
) -> InvoiceApprovalResponse | HTMLResponse:
    """
    Simulate the manager clicking the Approve button from their email.

    Logs the approval, transitions status, and sends the invoice to the client.
    """
    record = _pending_invoices.get(invoice_id)
    if record is None:
        raise api_error(status.HTTP_404_NOT_FOUND, ErrorCode.INVOICE_NOT_FOUND, extra={"invoice_id": invoice_id})

    if record["status"] == ProcessingStatus.APPROVED:
        raise api_error(status.HTTP_409_CONFLICT, ErrorCode.INVOICE_ALREADY_APPROVED, extra={"invoice_id": invoice_id})

    manager_email = record.get("manager_email", _settings.manager_email)
    client_email = record["client_email"]
    file_path = record["file_path"]

    _email_service.log_manager_approval(invoice_id, manager_email)
    _email_service.send_client_invoice_email(client_email, file_path)

    record["status"] = ProcessingStatus.APPROVED

    response = InvoiceApprovalResponse(
        invoice_id=invoice_id,
        status=ProcessingStatus.APPROVED,
        message="Invoice approved and sent to client.",
        client_email=client_email,
        file_path=file_path,
    )

    accept = request.headers.get("accept", "")
    wants_json = "application/json" in accept and "text/html" not in accept.split(",")[0]
    if not wants_json and ("text/html" in accept or "*/*" in accept):
        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><title>تأیید فاکتور</title></head>
<body style="font-family:Tahoma,sans-serif;max-width:520px;margin:40px auto;text-align:center;">
  <h2>✅ فاکتور با موفقیت تأیید شد</h2>
  <p>فاکتور <strong>{invoice_id}</strong> به آدرس <strong>{client_email}</strong> ارسال شد.</p>
  <p style="color:#666;font-size:14px;">{response.message}</p>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=200)

    return response


def _run_invoice_pipeline(client_text: str, client_email: str) -> InvoiceProcessResponse:
    logger.info("Processing invoice request | client_email=%s", mask_email(client_email))
    try:
        invoice_data = _llm_service.extract_invoice_data(client_text)
    except LLMServiceError as exc:
        logger.error("LLM extraction failed | error=%s", exc)
        raise api_error(exc.status_code, exc.error_code, message=str(exc)) from exc

    invoice_id = uuid.uuid4().hex[:12]
    invoice_dict = invoice_data.model_dump()
    invoice_dict["currency"] = invoice_data.currency.value

    try:
        file_path = _pdf_service.generate_invoice_file(invoice_dict)
    except Exception as exc:
        logger.exception("PDF generation failed | invoice_id=%s", invoice_id)
        raise api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.PDF_GENERATION_ERROR) from exc
    manager_email = _settings.manager_email

    try:
        _email_service.send_internal_approval_email(
            manager_email=manager_email,
            invoice_data=invoice_dict,
            file_path=file_path,
            invoice_id=invoice_id,
        )
    except Exception as exc:
        logger.exception("Approval email simulation failed | invoice_id=%s", invoice_id)
        raise api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.EMAIL_SEND_FAILED) from exc

    _pending_invoices[invoice_id] = {
        "invoice_id": invoice_id,
        "invoice_data": invoice_dict,
        "file_path": file_path,
        "client_email": client_email,
        "manager_email": manager_email,
        "status": ProcessingStatus.PENDING_APPROVAL,
    }

    return InvoiceProcessResponse(
        status=ProcessingStatus.PENDING_APPROVAL,
        message=(
            f"Invoice extracted and sent to {manager_email} for approval. "
            f"Approve at: {_settings.app_base_url}/api/v1/invoices/approve/{invoice_id}"
        ),
        invoice_id=invoice_id,
        invoice_data=invoice_data,
        pdf_path=file_path,
        email_stages=["internal_approval_sent"],
    )


async def _resolve_input_text(
    client_text: str | None,
    audio: UploadFile | None,
) -> tuple[str, InvoiceProcessResponse | None]:
    if client_text and client_text.strip():
        return client_text.strip(), None

    if audio is not None and audio.filename:
        audio_bytes = await audio.read()
        try:
            transcription = _stt_service.transcribe(audio_bytes, filename=audio.filename)
            if transcription in (STT_RATE_LIMIT_FALLBACK_MESSAGE, STT_TIMEOUT_FALLBACK_MESSAGE):
                logger.warning(
                    "STT graceful fallback engaged | filename=%s | reason=%s",
                    audio.filename,
                    "timeout" if transcription == STT_TIMEOUT_FALLBACK_MESSAGE else "rate_limit",
                )
                return "", _build_stt_fallback_response(transcription)
            return transcription, None
        except STTServiceError as exc:
            logger.warning(
                "Audio transcription failed, returning friendly fallback | status=%s | code=%s | error=%s",
                exc.status_code,
                exc.error_code,
                exc,
            )
            return "", _build_stt_fallback_response(STT_FALLBACK_MESSAGE)

    raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorCode.EMPTY_INPUT)


def _build_stt_fallback_response(message: str) -> InvoiceProcessResponse:
    audio_b64: str | None = None
    mime = "audio/mpeg"
    try:
        audio_bytes = _tts_service.text_to_speech(message)
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        logger.info("Generated fallback TTS audio | bytes=%d", len(audio_bytes))
    except TTSServiceError as exc:
        logger.warning("Fallback TTS unavailable | status=%s | error=%s", exc.status_code, exc)
        audio_b64 = None
    except Exception as exc:
        logger.exception("Unexpected error generating fallback TTS: %s", exc)
        audio_b64 = None

    return InvoiceProcessResponse(
        status=ProcessingStatus.FAILED,
        message=message,
        invoice_id=None,
        invoice_data=None,
        pdf_path=None,
        email_stages=["stt_fallback"],
        stt_fallback=True,
        fallback_audio_base64=audio_b64,
        fallback_audio_mime=mime if audio_b64 else None,
    )
