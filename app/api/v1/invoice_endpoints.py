import logging
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse

from app.config.settings import get_settings
from app.schemas.invoice_schemas import (
    InvoiceApprovalResponse,
    InvoiceData,
    InvoiceProcessResponse,
    InvoiceRequest,
    ProcessingStatus,
)
from app.services.email_service import EmailService
from app.services.llm_service import LLMService, LLMServiceError
from app.services.pdf_service import PDFService
from app.services.stt_service import STTService, STTServiceError

logger = logging.getLogger(__name__)

router = APIRouter()
_settings = get_settings()

_llm_service = LLMService()
_pdf_service = PDFService()
_email_service = EmailService()
_stt_service = STTService()

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
    text_input = await _resolve_input_text(client_text, audio)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{invoice_id}' not found or already processed.",
        )

    if record["status"] == ProcessingStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invoice '{invoice_id}' has already been approved.",
        )

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
    try:
        invoice_data = _llm_service.extract_invoice_data(client_text)
    except LLMServiceError as exc:
        logger.error("LLM extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    invoice_id = uuid.uuid4().hex[:12]
    invoice_dict = invoice_data.model_dump()
    invoice_dict["currency"] = invoice_data.currency.value

    file_path = _pdf_service.generate_invoice_file(invoice_dict)
    manager_email = _settings.manager_email

    _email_service.send_internal_approval_email(
        manager_email=manager_email,
        invoice_data=invoice_dict,
        file_path=file_path,
        invoice_id=invoice_id,
    )

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
) -> str:
    if client_text and client_text.strip():
        return client_text.strip()

    if audio is not None and audio.filename:
        audio_bytes = await audio.read()
        try:
            return _stt_service.transcribe(audio_bytes, filename=audio.filename)
        except STTServiceError as exc:
            logger.error("Audio transcription failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Either client_text or audio must be provided.",
    )
