"""Structured API errors with Persian user-facing messages."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ErrorCode:
    EMPTY_INPUT = "empty_input"
    VALIDATION_ERROR = "validation_error"
    API_KEY_MISSING = "api_key_missing"
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_PROVIDER = "llm_provider_error"
    LLM_UNREACHABLE = "llm_unreachable"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    EXTRACTION_FAILED = "extraction_failed"
    STT_TIMEOUT = "stt_timeout"
    STT_RATE_LIMIT = "stt_rate_limit"
    STT_PROVIDER = "stt_provider_error"
    STT_UNREACHABLE = "stt_unreachable"
    STT_EMPTY = "stt_empty"
    EMPTY_AUDIO = "empty_audio"
    PDF_GENERATION_ERROR = "pdf_generation_error"
    EMAIL_SEND_FAILED = "email_send_failed"
    INVOICE_NOT_FOUND = "invoice_not_found"
    INVOICE_ALREADY_APPROVED = "invoice_already_approved"
    UNEXPECTED = "unexpected_error"


MESSAGES_FA: dict[str, str] = {
    ErrorCode.EMPTY_INPUT: "متن یا فایل صوتی فاکتور ارسال نشده است. لطفاً یکی از آن‌ها را وارد کنید.",
    ErrorCode.VALIDATION_ERROR: "درخواست نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.",
    ErrorCode.API_KEY_MISSING: "پیکربندی سرویس هوش مصنوعی ناقص است. لطفاً با پشتیبانی تماس بگیرید.",
    ErrorCode.LLM_TIMEOUT: "استخراج اطلاعات فاکتور کمی طول کشید. لطفاً دوباره تلاش کنید.",
    ErrorCode.LLM_RATE_LIMIT: "سامانه موقتاً شلوغ است. لطفاً کمی بعد دوباره تلاش کنید.",
    ErrorCode.LLM_PROVIDER: "در پردازش فاکتور مشکلی پیش آمد. لطفاً دوباره تلاش کنید.",
    ErrorCode.LLM_UNREACHABLE: "ارتباط با سامانه هوش مصنوعی برقرار نشد. لطفاً دوباره تلاش کنید.",
    ErrorCode.LLM_INVALID_RESPONSE: "پاسخ سامانه برای استخراج فاکتور نامعتبر بود.",
    ErrorCode.EXTRACTION_FAILED: "اطلاعات فاکتور قابل استخراج نبود. لطفاً ورودی را واضح‌تر بیان کنید.",
    ErrorCode.STT_TIMEOUT: "تبدیل صدا به متن طول کشید. لطفاً کوتاه‌تر و واضح‌تر صحبت کنید.",
    ErrorCode.STT_RATE_LIMIT: "سرویس تشخیص گفتار موقتاً شلوغ است. لطفاً کمی بعد تلاش کنید.",
    ErrorCode.STT_PROVIDER: "متأسفانه صدای شما به‌درستی شنیده نشد. لطفاً دوباره تلاش کنید.",
    ErrorCode.STT_UNREACHABLE: "سرویس تشخیص گفتار در دسترس نیست. لطفاً دوباره تلاش کنید.",
    ErrorCode.STT_EMPTY: "متوجه صحبت شما نشدم. لطفاً نام مشتری، خدمات و مبلغ را بیان کنید.",
    ErrorCode.EMPTY_AUDIO: "فایل صوتی خالی است. لطفاً دوباره ضبط کنید.",
    ErrorCode.PDF_GENERATION_ERROR: "تولید فایل فاکتور با خطا مواجه شد. لطفاً دوباره تلاش کنید.",
    ErrorCode.EMAIL_SEND_FAILED: "ارسال ایمیل فاکتور انجام نشد. لطفاً با پشتیبانی تماس بگیرید.",
    ErrorCode.INVOICE_NOT_FOUND: "فاکتور مورد نظر یافت نشد یا قبلاً پردازش شده است.",
    ErrorCode.INVOICE_ALREADY_APPROVED: "این فاکتور قبلاً تأیید شده است.",
    ErrorCode.UNEXPECTED: "خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره تلاش کنید.",
}


def api_error(
    status_code: int,
    code: str,
    *,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> HTTPException:
    """Build an HTTPException with a stable JSON body for clients."""
    detail: dict[str, Any] = {
        "code": code,
        "message": message or MESSAGES_FA.get(code, MESSAGES_FA[ErrorCode.UNEXPECTED]),
    }
    if extra:
        detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def mask_email(email: str) -> str:
    """Mask an email address for safe logging."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"***@{domain}"
    return f"{local[:2]}***@{domain}"


def truncate(text: str, max_len: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1]}…"


def map_provider_status(status_code: int) -> int:
    """Map upstream HTTP status to a client-facing status."""
    if status_code == 429:
        return 429
    if status_code in {401, 403}:
        return 502
    if 400 <= status_code < 500:
        return 502
    if status_code >= 500:
        return 502
    return 502
