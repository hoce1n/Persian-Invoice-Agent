import logging
import uuid
from pathlib import Path

import arabic_reshaper
import jdatetime
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

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
    """Generates Persian RTL PDF invoices in the generated_invoices/ directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._font_regular = "Vazirmatn-Regular"
        self._font_bold = "Vazirmatn-Bold"
        self._register_fonts()

    def _register_fonts(self) -> None:
        regular_path = Path(self._settings.pdf_font_regular_path)
        bold_path = Path(self._settings.pdf_font_bold_path)
        if not regular_path.exists() or not bold_path.exists():
            raise FileNotFoundError(
                f"Persian font files not found. regular={regular_path} bold={bold_path}"
            )
        pdfmetrics.registerFont(TTFont(self._font_regular, str(regular_path)))
        pdfmetrics.registerFont(TTFont(self._font_bold, str(bold_path)))

    @staticmethod
    def _rtl(text: str) -> str:
        return get_display(arabic_reshaper.reshape(text))

    @staticmethod
    def _persian_digits(value: str) -> str:
        table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        return value.translate(table)

    def generate_invoice_file(self, invoice_data: dict) -> str:
        """Create a production-style Persian RTL invoice PDF and return its absolute path."""
        output_dir = Path(self._settings.pdf_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        invoice_id = uuid.uuid4().hex[:12]
        filename = f"invoice_{invoice_id}.pdf"
        file_path = output_dir / filename

        client_name = str(invoice_data.get("client_name", "نامشخص"))
        clinic_name = str(invoice_data.get("clinic_name", "نامشخص"))
        service_description = str(invoice_data.get("service_description", "—"))
        invoice_date = str(invoice_data.get("invoice_date_shamsi", "نامشخص"))
        invoice_number = str(invoice_data.get("invoice_number", "AUTO"))
        notes = str(invoice_data.get("notes", "")).strip()
        amount = float(invoice_data.get("amount", 0))
        tax_amount = float(invoice_data.get("tax_amount", 0))
        discount_amount = float(invoice_data.get("discount_amount", 0))
        payable_amount = float(invoice_data.get("payable_amount", amount + tax_amount - discount_amount))
        currency_code = invoice_data.get("currency", "IRR")
        if hasattr(currency_code, "value"):
            currency_code = currency_code.value
        currency_fa = _CURRENCY_FA.get(str(currency_code), str(currency_code))

        issue_date = invoice_date if invoice_date != "نامشخص" else jdatetime.datetime.now().strftime("%Y/%m/%d")
        issue_date = self._persian_digits(issue_date)
        invoice_number_fa = self._persian_digits(invoice_number)

        def money(value: float) -> str:
            return f"{value:,.0f} {currency_fa}"

        pdf = canvas.Canvas(str(file_path), pagesize=A4)
        width, height = A4
        right_margin = width - 45
        left_margin = 45
        y = height - 55

        pdf.setFillColor(colors.HexColor("#0f172a"))
        pdf.rect(0, height - 130, width, 130, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont(self._font_bold, 20)
        pdf.drawRightString(right_margin, y, self._rtl("صورتحساب رسمی"))
        y -= 28
        pdf.setFont(self._font_regular, 11)
        pdf.drawRightString(right_margin, y, self._rtl(f"شماره فاکتور: {invoice_number_fa}"))
        y -= 18
        pdf.drawRightString(right_margin, y, self._rtl(f"تاریخ صدور: {issue_date}"))
        y -= 18
        pdf.drawRightString(right_margin, y, self._rtl(f"شناسه داخلی: {invoice_id}"))

        y = height - 170
        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.roundRect(left_margin, y - 78, width - 90, 78, 8, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#f9fafb"))
        pdf.setFont(self._font_bold, 12)
        pdf.drawRightString(right_margin - 10, y - 20, self._rtl("اطلاعات طرفین"))
        pdf.setFont(self._font_regular, 10.5)
        pdf.drawRightString(right_margin - 10, y - 42, self._rtl(f"نام مشتری: {client_name}"))
        pdf.drawRightString(right_margin - 240, y - 42, self._rtl(f"نام کلینیک/مرکز: {clinic_name}"))

        y -= 110
        pdf.setFillColor(colors.HexColor("#e5e7eb"))
        pdf.roundRect(left_margin, y - 154, width - 90, 154, 8, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.setFont(self._font_bold, 11.5)
        pdf.drawRightString(right_margin - 10, y - 20, self._rtl("شرح خدمات"))
        pdf.setFont(self._font_regular, 10.5)
        pdf.drawRightString(right_margin - 10, y - 44, self._rtl(service_description))

        # Pricing rows
        base_y = y - 78
        rows = [
            ("مبلغ پایه", money(amount)),
            ("مالیات", money(tax_amount)),
            ("تخفیف", money(discount_amount)),
            ("مبلغ قابل پرداخت", money(payable_amount)),
        ]
        for idx, (label, value) in enumerate(rows):
            row_y = base_y - (idx * 22)
            if idx == 3:
                pdf.setFillColor(colors.HexColor("#111827"))
                pdf.roundRect(left_margin + 14, row_y - 15, width - 118, 20, 5, stroke=0, fill=1)
                pdf.setFillColor(colors.white)
                font_name = self._font_bold
            else:
                pdf.setFillColor(colors.HexColor("#111827"))
                font_name = self._font_regular
            pdf.setFont(font_name, 10.5)
            pdf.drawRightString(right_margin - 18, row_y, self._rtl(label))
            pdf.drawString(left_margin + 24, row_y, self._rtl(self._persian_digits(value)))

        y -= 182
        if notes:
            pdf.setFillColor(colors.HexColor("#374151"))
            pdf.setFont(self._font_regular, 9.5)
            pdf.drawRightString(right_margin - 10, y, self._rtl(f"یادداشت: {notes}"))
            y -= 20

        pdf.setStrokeColor(colors.HexColor("#9ca3af"))
        pdf.line(left_margin, y, width - left_margin, y)
        y -= 15
        pdf.setFillColor(colors.HexColor("#4b5563"))
        pdf.setFont(self._font_regular, 8.5)
        pdf.drawRightString(
            right_margin,
            y,
            self._rtl("این سند به صورت خودکار توسط Persian Invoice Agent تولید شده است."),
        )

        pdf.save()
        logger.info("Invoice PDF generated at %s", file_path)
        return str(file_path.resolve())

    def generate_invoice_pdf(self, invoice_data: InvoiceData) -> str:
        """Backward-compatible wrapper around generate_invoice_file."""
        payload = invoice_data.model_dump()
        payload["currency"] = invoice_data.currency.value
        return self.generate_invoice_file(payload)
