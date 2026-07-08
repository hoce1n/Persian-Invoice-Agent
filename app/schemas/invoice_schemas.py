from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Currency(str, Enum):
    IRR = "IRR"
    IRT = "IRT"
    USD = "USD"
    EUR = "EUR"


class InvoiceData(BaseModel):
    """Structured invoice fields extracted from Persian voice or text input."""

    client_name: str = Field(..., description="Name of the client or customer")
    clinic_name: str = Field(default="—", description="Clinic or business name")
    service_description: str = Field(..., description="Description of the service or product")
    invoice_date_shamsi: str = Field(default="نامشخص", description="Persian (Jalali) invoice date")
    invoice_number: str = Field(default="AUTO", description="Invoice or receipt reference number")
    tax_amount: float = Field(default=0, ge=0, description="Tax amount")
    discount_amount: float = Field(default=0, ge=0, description="Discount amount")
    amount: float = Field(..., gt=0, description="Invoice amount as a positive number")
    payable_amount: float | None = Field(default=None, gt=0, description="Final payable amount")
    currency: Currency = Field(default=Currency.IRR, description="ISO-style currency code")
    notes: str = Field(default="", description="Additional invoice notes")

    @model_validator(mode="after")
    def ensure_payable_amount(self) -> "InvoiceData":
        if self.payable_amount is None:
            computed = self.amount + self.tax_amount - self.discount_amount
            self.payable_amount = computed if computed > 0 else self.amount
        return self


class InvoiceRequest(BaseModel):
    """Request payload for invoice processing via text input."""

    client_text: str | None = Field(
        default=None,
        min_length=1,
        description="Persian text describing the invoice request",
    )
    client_email: str | None = Field(
        default=None,
        description="Client email for invoice delivery after approval",
    )

    @model_validator(mode="after")
    def validate_has_text(self) -> "InvoiceRequest":
        if not self.client_text or not self.client_text.strip():
            raise ValueError("client_text is required and cannot be empty")
        return self


class ProcessingStatus(str, Enum):
    EXTRACTED = "extracted"
    PDF_GENERATED = "pdf_generated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EMAIL_QUEUED = "email_queued"
    COMPLETED = "completed"
    FAILED = "failed"


class InvoiceProcessResponse(BaseModel):
    """Response returned after processing an invoice request."""

    status: ProcessingStatus
    message: str
    invoice_id: str | None = None
    invoice_data: InvoiceData | None = None
    pdf_path: str | None = None
    email_stages: list[str] = Field(default_factory=list)
    stt_fallback: bool = False
    fallback_audio_base64: str | None = None
    fallback_audio_mime: str | None = None


class InvoiceApprovalResponse(BaseModel):
    """Response returned after a manager approves an invoice."""

    invoice_id: str
    status: ProcessingStatus
    message: str
    client_email: str
    file_path: str
