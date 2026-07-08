"""User-facing fallback messages for graceful degradation."""

EXTRACTION_FALLBACK_MESSAGE = (
    "متأسفانه اطلاعات فاکتور به‌درستی استخراج نشد. "
    "لطفاً نام مشتری، شرح خدمات و مبلغ را واضح‌تر بیان کنید."
)

STT_FALLBACK_MESSAGE = (
    "متوجه صحبت شما نشدم. لطفاً دوباره نام مشتری، خدمات و مبلغ را بیان کنید."
)

# Spoken fallback when STT hits rate limits after retries.
STT_RATE_LIMIT_FALLBACK_MESSAGE = (
    "متأسفانه سرویس تشخیص گفتار موقتاً شلوغ است. "
    "لطفاً متن را تایپ کنید یا کمی بعد دوباره امتحان کنید."
)

# Spoken fallback when STT times out after retry.
STT_TIMEOUT_FALLBACK_MESSAGE = (
    "پاسخ سرویس تشخیص گفتار طول کشید. "
    "لطفاً متن را تایپ کنید یا کمی بعد دوباره امتحان کنید."
)
