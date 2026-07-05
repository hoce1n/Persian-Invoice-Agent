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
    service_description: str = Field(..., description="Description of the service or product")
    amount: float = Field(..., gt=0, description="Invoice amount as a positive number")
    currency: Currency = Field(default=Currency.IRR, description="ISO-style currency code")


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


class InvoiceApprovalResponse(BaseModel):
    """Response returned after a manager approves an invoice."""

    invoice_id: str
    status: ProcessingStatus
    message: str
    client_email: str
    file_path: str
