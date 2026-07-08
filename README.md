# Persian Invoice Agent

یک سرویس **AI-powered** برای خودکارسازی چرخه صدور فاکتور فارسی: دریافت متن/صوت، استخراج داده ساخت‌یافته، تولید **PDF RTL**، و جریان **Human-in-the-Loop Approval**.

این پروژه همراه **Persian Voice Agent** طراحی شده است. Voice Agent مکالمه صوتی را مدیریت می‌کند و در صورت نیاز، درخواست فاکتور را به این سرویس ارسال می‌کند.

---

## Features Delivered

| Area | Capability |
|---|---|
| Input | متن فارسی یا فایل صوتی (Whisper-compatible STT) |
| Extraction | LLM با فیلدهای ایرانی: نام مشتری، نام کلینیک، تاریخ شمسی، مبلغ، مالیات، تخفیف، جمع قابل پرداخت |
| Output | PDF فارسی RTL با فونت Vazirmatn و تاریخ شمسی |
| Approval | ارسال شبیه‌سازی‌شده به مدیر + endpoint تأیید + ارسال نهایی به مشتری |
| Ops | `/health`, `/api/v1/status`, داشبورد `/status` |
| Errors | کدهای پایدار (`code`) + پیام فارسی (`message`) |

---

## Integration with Voice Agent

| Service | Port | Health |
|---|---|---|
| Persian Voice Agent | `8000` | `GET /health` |
| Persian Invoice Agent | `8001` | `GET /health` |

در Voice Agent:

```env
INVOICE_AGENT_URL=http://localhost:8001
```

در Invoice Agent:

```env
VOICE_AGENT_URL=http://localhost:8000
APP_BASE_URL=http://localhost:8001
```

Voice Agent وضعیت Invoice Agent را در `checks.invoice_agent` و Invoice Agent وضعیت Voice Agent را در `checks.voice_agent` گزارش می‌دهد.

---

## Tech Stack

- FastAPI + Uvicorn
- OpenAI-compatible LLM + Whisper STT
- ReportLab + arabic-reshaper + python-bidi + jdatetime
- Tailwind RTL UI + Status Dashboard

---

## Project Structure

```text
persian-invoice-agent/
├── .env.template
├── README.md
├── requirements.txt
├── run.bat
└── app/
    ├── main.py
    ├── api/v1/
    │   ├── invoice_endpoints.py
    │   ├── status_endpoints.py
    │   └── router.py
    ├── assets/fonts/          # Vazirmatn font files
    ├── config/
    │   ├── settings.py
    │   └── logging_config.py
    ├── core/
    │   ├── errors.py
    │   └── messages.py
    ├── prompts/
    │   └── invoice_extractor.py
    ├── schemas/
    │   └── invoice_schemas.py
    ├── services/
    │   ├── llm_service.py
    │   ├── stt_service.py
    │   ├── pdf_service.py
    │   ├── email_service.py
    │   └── voice_agent_service.py
    └── static/
        ├── index.html
        └── status.html
```

---

## Quick Start (Windows)

```powershell
cd C:\Users\Iranian\Desktop\project\persian-invoice-agent
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.template .env
python -m uvicorn app.main:app --reload --port 8001
```

یا:

```powershell
.\run.bat
```

### Useful URLs

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8001/` | Invoice UI |
| `http://127.0.0.1:8001/status` | Status dashboard |
| `http://127.0.0.1:8001/docs` | Swagger |
| `http://127.0.0.1:8001/health` | Liveness probe |
| `http://127.0.0.1:8001/api/v1/status` | Full JSON status |

### Run alongside Voice Agent

```powershell
# Terminal 1
cd ..\persian-voice-agent
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2
cd ..\persian-invoice-agent
python -m uvicorn app.main:app --reload --port 8001
```

---

## Environment Variables

| Key | Required | Default | Description |
|---|---|---|---|
| `APP_NAME` | No | Persian Invoice Agent | نام سرویس |
| `APP_BASE_URL` | Yes | `http://localhost:8001` | Base URL لینک تأیید |
| `LLM_API_KEY` | Yes | — | کلید LLM/STT Gateway |
| `LLM_BASE_URL` | Yes | OpenAI URL | آدرس Gateway |
| `LLM_MODEL` | Yes | `gpt-4o-mini` | مدل استخراج |
| `WHISPER_MODEL` | Yes | `whisper-1` | مدل STT |
| `MANAGER_EMAIL` | Yes | — | ایمیل مدیر |
| `DEFAULT_CLIENT_EMAIL` | Yes | — | ایمیل پیش‌فرض مشتری |
| `PDF_OUTPUT_DIR` | No | `./generated_invoices` | مسیر خروجی PDF |
| `PDF_FONT_REGULAR_PATH` | No | `./app/assets/fonts/Vazirmatn-Regular.ttf` | فونت معمولی |
| `PDF_FONT_BOLD_PATH` | No | `./app/assets/fonts/Vazirmatn-Bold.ttf` | فونت Bold |
| `VOICE_AGENT_URL` | No | `http://localhost:8000` | آدرس Voice Agent |
| `LOG_LEVEL` | No | `INFO` | سطح لاگ |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/process-invoice-request` | پردازش multipart (متن/صوت) |
| `POST` | `/api/v1/process-invoice-request/json` | پردازش JSON |
| `GET` | `/api/v1/invoices/approve/{invoice_id}` | تأیید فاکتور توسط مدیر |
| `GET` | `/api/v1/status` | وضعیت سرویس و وابستگی‌ها |
| `GET` | `/health` | Liveness (`status`, `version`) |

### Extracted Invoice Fields

- `client_name`, `clinic_name`
- `service_description`, `invoice_date_shamsi`, `invoice_number`
- `amount`, `tax_amount`, `discount_amount`, `payable_amount`
- `currency`, `notes`

---

## Resilience & Error Handling

- خطاهای API با ساختار یکسان:

```json
{
  "detail": {
    "code": "llm_timeout",
    "message": "استخراج اطلاعات فاکتور کمی طول کشید..."
  }
}
```

- Timeout/rate-limit/provider errors برای LLM و STT
- Global handlers برای validation و unexpected errors
- Masking ایمیل در لاگ‌ها (`ma***@example.com`)

---

## Known Limitations

| Limitation | Notes |
|---|---|
| In-memory approval store | برای production نیاز به DB |
| Email simulated | SMTP/SendGrid هنوز placeholder است |
| Single-instance state | در چند replica نیاز به shared storage |

---

## Troubleshooting

1. **PDF generation error**  
   بررسی کنید فونت‌های `Vazirmatn-Regular.ttf` و `Vazirmatn-Bold.ttf` در `app/assets/fonts/` موجود باشند.

2. **Voice Agent unreachable in status**  
   Voice Agent را روی پورت `8000` اجرا کنید یا `VOICE_AGENT_URL` را اصلاح کنید.

3. **Approval link wrong host**  
   `APP_BASE_URL` باید `http://localhost:8001` (یا دامنه production) باشد.

---

## License

برای استفاده داخلی/آزمایشی توسعه داده شده است. برای انتشار عمومی، افزودن لایسنس (مثلاً MIT) توصیه می‌شود.
