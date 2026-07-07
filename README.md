# Persian Invoice Agent

یک پلتفرم **AI-powered** برای خودکارسازی چرخه صدور فاکتور، از دریافت ورودی متنی/صوتی فارسی تا استخراج داده ساخت‌یافته، تولید فایل فاکتور، و ارسال در جریان **Human-in-the-Loop Approval**.

این پروژه برای کسب‌وکارهایی طراحی شده که می‌خواهند فرآیند زمان‌بر صدور فاکتور را از حالت دستی خارج کنند:  
کاربر درخواست را به‌صورت متن یا صدا ارسال می‌کند، سیستم با استفاده از **LLM Gateway** و **Whisper-compatible STT** اطلاعات فاکتور را استخراج می‌کند، پیش‌نویس فاکتور را می‌سازد، برای مدیر ارسال می‌کند و پس از تایید، ارسال نهایی به مشتری انجام می‌شود.

**Tech Stack اصلی:**
- **FastAPI** برای API backend
- **Uvicorn** برای ASGI server
- **Requests** برای ارتباط با LLM Gateway
- **OpenAI-compatible API** (Chat Completions + Whisper Transcription)
- **Tailwind CSS (CDN)** + Vanilla JS برای UI تعاملی و Dark Theme

---

## Key Features

- دریافت ورودی فاکتور به دو روش:
  - متن فارسی
  - صدای فارسی (با `MediaRecorder` و STT)
- تبدیل صوت به متن با **Whisper-compatible endpoint**
- استخراج Entityهای فاکتور با LLM:
  - `client_name`
  - `service_description`
  - `amount`
  - `currency`
- پاکسازی و Parse خروجی JSON حتی در صورت بازگشت در قالب Markdown code block
- تولید محلی فایل فاکتور در پوشه `generated_invoices/`
- جریان تایید مدیریتی (**Human-in-the-Loop**):
  - ارسال پیش‌نویس برای مدیر
  - Endpoint تایید
  - ارسال نهایی برای مشتری پس از Approval
- رابط کاربری حرفه‌ای RTL (فارسی) با Dark Mode، Badgeهای وضعیت و Live Log
- Provider-agnostic: تعویض آسان سرویس AI از طریق Environment Variables

---

## Project Structure

```text
persian-invoice-agent/
├── .env.template
├── .gitignore
├── README.md
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
    │   ├── __init__.py
    │   └── v1/
    │       ├── __init__.py
    │       ├── invoice_endpoints.py
    │       └── router.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── prompts/
    │   ├── __init__.py
    │   └── invoice_extractor.py
    ├── schemas/
    │   ├── __init__.py
    │   └── invoice_schemas.py
    ├── services/
    │   ├── __init__.py
    │   ├── email_service.py
    │   ├── llm_service.py
    │   ├── pdf_service.py
    │   └── stt_service.py
    └── static/
        └── index.html
```

---

## Prerequisites & Installation (Windows)

### 1) پیش‌نیازها
- **Python 3.10+** (ترجیحا 3.11 یا بالاتر)
- **pip**
- دسترسی اینترنت برای فراخوانی LLM Gateway

### 2) ساخت Virtual Environment

```powershell
cd C:\Users\Iranian\Desktop\project\persian-invoice-agent
python -m venv venv
```

### 3) فعال‌سازی محیط مجازی

```powershell
.\venv\Scripts\activate
```

### 4) نصب وابستگی‌ها

```powershell
pip install -r requirements.txt
```

### 5) آماده‌سازی فایل محیطی

```powershell
copy .env.template .env
```

سپس مقادیر واقعی (به‌خصوص `LLM_API_KEY` و `LLM_BASE_URL`) را در `.env` وارد کنید.

---

## How to Run

این ریپو، **Invoice Agent** است؛ بنابراین اجرای پیشنهادی روی پورت `8001`:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

پس از اجرا:
- UI: `http://127.0.0.1:8001/`
- Swagger: `http://127.0.0.1:8001/docs`
- Health: `http://127.0.0.1:8001/health`

> اگر پروژه‌ای با نقش **Voice Agent** دارید، طبق قرارداد شما می‌توانید آن را روی پورت `8000` اجرا کنید.

---

## Environment Variables

| Key | Required | Description |
|---|---|---|
| `APP_NAME` | No | نام نمایشی سرویس |
| `APP_ENV` | No | محیط اجرا (`development`/`production`) |
| `APP_BASE_URL` | Yes | Base URL مورد استفاده در لینک‌های تایید |
| `DEBUG` | No | فعال/غیرفعال بودن لاگ سطح Debug |
| `LLM_API_KEY` | Yes | کلید دسترسی به LLM Gateway (OpenAI-compatible) |
| `LLM_BASE_URL` | Yes | آدرس پایه API (مثلا `https://api.openai.com/v1`) |
| `LLM_MODEL` | Yes | مدل LLM برای استخراج داده فاکتور |
| `WHISPER_MODEL` | Yes | مدل STT برای تبدیل صوت به متن |
| `EMAIL_SERVICE_API_KEY` | No | Placeholder برای سرویس ایمیل واقعی |
| `EMAIL_FROM_ADDRESS` | Yes | فرستنده ایمیل‌های شبیه‌سازی‌شده |
| `EMAIL_APPROVAL_RECIPIENT` | No | گیرنده داخلی برای جریان Approval |
| `MANAGER_EMAIL` | Yes | ایمیل مدیر برای تایید فاکتور |
| `DEFAULT_CLIENT_EMAIL` | Yes | ایمیل پیش‌فرض مشتری در صورت عدم ارسال از UI |
| `PDF_OUTPUT_DIR` | Yes | مسیر خروجی فایل‌های فاکتور تولیدشده |

### مثال تنظیم Provider

```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# یا هر Gateway سازگار با OpenAI
LLM_BASE_URL=https://your-gateway.example.com/v1
LLM_MODEL=your-model-alias
```

---

## Important Notes

### خطاهای رایج AI Gateway

| Status | علت احتمالی | اقدام |
|---|---|---|
| `401` | کلید API نامعتبر یا منقضی | `LLM_API_KEY` را بررسی و جایگزین کنید |
| `403` | محدودیت Provider (پلن، Verification، دسترسی مدل) | پنل Provider را بررسی کنید |
| `429` | Rate limit یا سقف مصرف | کمی صبر کنید یا پلن را ارتقا دهید |
| `502/503` | مدل یا Gateway موقتا در دسترس نیست | مدل دیگری امتحان کنید یا Retry کنید |

پیام‌های خطا در UI و Backend به‌صورت **AI Service Error** نمایش داده می‌شوند.

---

## API Quick Reference

- `POST /api/v1/process-invoice-request`  
  پردازش ورودی `multipart/form-data` (متن یا فایل صوتی)
- `POST /api/v1/process-invoice-request/json`  
  پردازش JSON برای کلاینت‌های برنامه‌نویسی
- `GET /api/v1/invoices/approve/{invoice_id}`  
  تایید فاکتور توسط مدیر و ارسال نهایی برای مشتری

---

## License

برای استفاده داخلی/آزمایشی توسعه داده شده است. در صورت انتشار عمومی، توصیه می‌شود لایسنس مناسب (مثلا MIT) به پروژه اضافه شود.