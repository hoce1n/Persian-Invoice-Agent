import logging
import textwrap

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_BLOCK_WIDTH = 72


def _log_email_block(title: str, body: str) -> None:
    border = "=" * _BLOCK_WIDTH
    header = f"  {title}"
    logger.info("\n%s\n%s\n%s\n%s", border, header, border, body)


class EmailService:
    """Human-in-the-loop email simulation for invoice approval workflows."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def send_internal_approval_email(
        self,
        manager_email: str,
        invoice_data: dict,
        file_path: str,
        invoice_id: str,
    ) -> bool:
        """
        Simulate sending the draft invoice to the business owner for approval.

        Includes a mock approval link the manager can click.
        """
        client_name = invoice_data.get("client_name", "—")
        clinic_name = invoice_data.get("clinic_name", "—")
        service = invoice_data.get("service_description", "—")
        amount = invoice_data.get("amount", 0)
        payable_amount = invoice_data.get("payable_amount", amount)
        tax_amount = invoice_data.get("tax_amount", 0)
        discount_amount = invoice_data.get("discount_amount", 0)
        invoice_date = invoice_data.get("invoice_date_shamsi", "نامشخص")
        currency = invoice_data.get("currency", "IRR")
        if hasattr(currency, "value"):
            currency = currency.value

        approval_url = (
            f"{self._settings.app_base_url.rstrip('/')}"
            f"/api/v1/invoices/approve/{invoice_id}"
        )

        body = textwrap.dedent(f"""
            From   : {self._settings.email_from_address}
            To     : {manager_email}
            Subject: [نیاز به تأیید] پیش‌نویس فاکتور — {client_name}

            سلام،

            یک پیش‌نویس فاکتور جدید آماده بررسی است:

              • مشتری  : {client_name}
              • کلینیک : {clinic_name}
              • خدمات  : {service}
              • تاریخ  : {invoice_date}
              • مبلغ پایه: {amount:,.0f} {currency}
              • مالیات : {tax_amount:,.0f} {currency}
              • تخفیف  : {discount_amount:,.0f} {currency}
              • قابل پرداخت: {payable_amount:,.0f} {currency}
              • فایل   : {file_path}

            برای تأیید و ارسال به مشتری، روی لینک زیر کلیک کنید:

              {approval_url}

            ─────────────────────────────────────
            این ایمیل به‌صورت شبیه‌سازی‌شده ارسال شده است.
        """).strip()

        _log_email_block("STAGE 1 — INTERNAL APPROVAL EMAIL (→ Manager)", body)
        return True

    def send_client_invoice_email(self, client_email: str, file_path: str) -> bool:
        """
        Simulate delivering the approved invoice to the client.

        Triggered only after the manager approves via the approval link.
        """
        body = textwrap.dedent(f"""
            From   : {self._settings.email_from_address}
            To     : {client_email}
            Subject: صورتحساب رسمی — پیوست فاکتور

            با سلام،

            فاکتور تأیید‌شده شما آماده است. لطفاً فایل پیوست را بررسی فرمایید.

              • فایل پیوست : {file_path}

            با تشکر،
            {self._settings.app_name}

            ─────────────────────────────────────
            این ایمیل به‌صورت شبیه‌سازی‌شده ارسال شده است.
        """).strip()

        _log_email_block("STAGE 2 — CLIENT INVOICE EMAIL (→ Customer)", body)
        return True

    def log_manager_approval(self, invoice_id: str, manager_email: str) -> None:
        """Log the manager's approval action as a distinct console block."""
        body = textwrap.dedent(f"""
            Invoice ID : {invoice_id}
            Approved by: {manager_email}
            Action     : Manager clicked "Approve" in email
            Status     : pending_approval → approved
        """).strip()

        _log_email_block("STAGE 1.5 — MANAGER APPROVAL RECEIVED", body)
