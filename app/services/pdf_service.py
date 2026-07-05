import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import Settings, get_settings
from app.schemas.invoice_schemas import InvoiceData

logger = logging.getLogger(__name__)

_CURRENCY_FA = {
    "IRR": "ریال",
    "IRT": "تومان",
    "USD": "دلار",
    "EUR": "یورو",
}


class PDFService:
    """Generates structured invoice files in the generated_invoices/ directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def generate_invoice_file(self, invoice_data: dict) -> str:
        """
        Create a structured markdown invoice file with Persian layout.

        Returns the absolute local file path.
        """
        output_dir = Path(self._settings.pdf_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        invoice_id = uuid.uuid4().hex[:12]
        filename = f"invoice_{invoice_id}.md"
        file_path = output_dir / filename

        client_name = invoice_data.get("client_name", "—")
        service_description = invoice_data.get("service_description", "—")
        amount = invoice_data.get("amount", 0)
        currency_code = invoice_data.get("currency", "IRR")
        if hasattr(currency_code, "value"):
            currency_code = currency_code.value
        currency_fa = _CURRENCY_FA.get(str(currency_code), str(currency_code))

        issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        formatted_amount = f"{amount:,.0f}"

        content = f"""# صورتحساب رسمی

---

| | |
|---|---|
| **شماره فاکتور** | `{invoice_id}` |
| **تاریخ صدور** | {issued_at} |

---

## مشخصات مشتری

**نام مشتری:** {client_name}

---

## شرح خدمات

{service_description}

---

## مبلغ قابل پرداخت

| ردیف | شرح | مبلغ |
|:---:|:---|---:|
| ۱ | {service_description} | **{formatted_amount} {currency_fa}** |

---

### جمع کل

**{formatted_amount} {currency_fa}** ({currency_code})

---

> این سند به‌صورت خودکار توسط سامانه صدور فاکتور هوشمند تولید شده است.
"""

        file_path.write_text(content, encoding="utf-8")
        logger.info("Invoice file generated at %s", file_path)
        return str(file_path.resolve())

    def generate_invoice_pdf(self, invoice_data: InvoiceData) -> str:
        """Backward-compatible wrapper around generate_invoice_file."""
        payload = invoice_data.model_dump()
        payload["currency"] = invoice_data.currency.value
        return self.generate_invoice_file(payload)
