# Persian Invoice Agent

یک پلتفرم **AI-powered** برای خودکارسازی چرخه صدور فاکتور، از دریافت ورودی متنی/صوتی فارسی تا استخراج داده ساخت‌یافته، تولید فایل فاکتور، و ارسال در جریان **Human-in-the-Loop Approval**.

این پروژه برای کسب‌وکارهایی طراحی شده که می‌خواهند فرآیند زمان‌بر صدور فاکتور را از حالت دستی خارج کنند:  
کاربر درخواست را به‌صورت متن یا صدا ارسال می‌کند، سیستم با استفاده از **Bynara DeepSeek/Whisper** اطلاعات فاکتور را استخراج می‌کند، پیش‌نویس فاکتور را می‌سازد، برای مدیر ارسال می‌کند و پس از تایید، ارسال نهایی به مشتری انجام می‌شود.

**Tech Stack اصلی:**
- **FastAPI** برای API backend
- **Uvicorn** برای ASGI server
- **Requests** برای ارتباط با Bynara API
- **Bynara Router** (Chat Completions + Whisper Transcription)
- **Tailwind CSS (CDN)** + Vanilla JS برای UI تعاملی و Dark Theme

---

## Key Features

- دریافت ورودی فاکتور به دو روش:
  - متن فارسی
  - صدای فارسی (با `MediaRecorder` و STT)
- تبدیل صوت به متن با **Whisper-compatible endpoint** در Bynara
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
- دسترسی اینترنت برای فراخوانی Bynara API

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

سپس مقادیر واقعی (به‌خصوص `BYNARA_API_KEY`) را در `.env` وارد کنید.

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
| `BYNARA_API_KEY` | Yes | کلید دسترسی Bynara Router |
| `BYNARA_BASE_URL` | Yes | آدرس پایه API (معمولا `https://router.bynara.id/v1`) |
| `BYNARA_MODEL` | Yes | مدل LLM برای استخراج داده فاکتور |
| `WHISPER_MODEL` | Yes | مدل STT برای تبدیل صوت به متن |
| `EMAIL_SERVICE_API_KEY` | No | Placeholder برای سرویس ایمیل واقعی |
| `EMAIL_FROM_ADDRESS` | Yes | فرستنده ایمیل‌های شبیه‌سازی‌شده |
| `EMAIL_APPROVAL_RECIPIENT` | No | گیرنده داخلی برای جریان Approval |
| `MANAGER_EMAIL` | Yes | ایمیل مدیر برای تایید فاکتور |
| `DEFAULT_CLIENT_EMAIL` | Yes | ایمیل پیش‌فرض مشتری در صورت عدم ارسال از UI |
| `PDF_OUTPUT_DIR` | Yes | مسیر خروجی فایل‌های فاکتور تولیدشده |

---

## Important Notes

### 403 Forbidden از Bynara (telegram_required)

اگر خطای زیر را دریافت کردید:

```text
403 forbidden: telegram_required
Join the required Telegram group/channel and relink at /settings
```

به معنی مشکل کدنویسی نیست؛ حساب Bynara شما نیاز به Verification دارد.

**راه‌حل:**
1. وارد پنل Bynara شوید.
2. گروه/کانال Telegram اجباری را Join کنید.
3. در صفحه Settings، حساب را Relink کنید.
4. سرور را ری‌استارت کنید و مجدد تست بگیرید.

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

