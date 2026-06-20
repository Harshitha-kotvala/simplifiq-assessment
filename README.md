# LeadFlow AI: Automated Lead Enrichment & Reporting Platform

A fully automated lead intake pipeline: form submission → company enrichment → personalized PDF report → email delivery.

---

## What It Does

When a prospect submits the form:

1. Validates the submission with Pydantic.
2. Enriches company data by scraping the website, running a Google fallback search, and synthesizing intelligence with Gemini.
3. Generates a personalized PDF audit report using Gemini + Jinja2 + pdfkit.
4. Emails the report via Gmail SMTP with the PDF attached.

Everything happens in a background thread. The form returns a confirmation instantly.

---

## Architecture

```text
[HTML Form] -> POST /submit -> [FastAPI]
                                 |
                   +-------------+-------------+
                   |             |             |
              enrichment.py   report.py   email_sender.py
              scrape website   Gemini writes   Gmail SMTP email
              Google fallback   report content  + PDF attachment
              Gemini synthesis  Jinja2 template
```

---

## Project Structure

```text
leadflow-ai/
├── backend/
│   ├── main.py              # FastAPI app, /submit endpoint
│   ├── enrichment.py        # Web scraping + Gemini synthesis
│   ├── report.py            # Report content generation + PDF rendering
│   ├── email_sender.py      # Gmail SMTP email with PDF attachment
│   └── requirements.txt
├── frontend/
│   └── index.html           # Lead capture form
├── templates/
│   └── report_template.html # Jinja2 + pdfkit HTML-to-PDF template
├── output/                  # Generated PDFs (auto-created)
├── .env.example
└── README.md
```

---

## Setup

### 1. Clone & Install

```bash
git clone <repo>
cd leadflow-ai/backend
pip install -r requirements.txt
```

### 2. Install wkhtmltopdf

`pdfkit` uses `wkhtmltopdf` under the hood, so install it separately.

- Download the installer from https://wkhtmltopdf.org/downloads.html
- Install it and make sure `wkhtmltopdf.exe` is available on your PATH

### 3. Configure Environment

```bash
cp .env.example .env
# Fill in all values in .env
```

Required:

- `GEMINI_API_KEY` — Gemini API key
- `GMAIL_ADDRESS` — Gmail address used to send the report
- `GMAIL_APP_PASSWORD` — Gmail App Password for SMTP login

### 4. Gmail App Password Setup

1. Go to https://myaccount.google.com/ and open Security
2. Enable 2-Step Verification
3. Open https://myaccount.google.com/apppasswords
4. Create an app password and paste it into `GMAIL_APP_PASSWORD`

---

## Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` and the form loads automatically.

---

## API

### `POST /submit`

```json
{
  "name": "Priya Sharma",
  "email": "priya@zomato.com",
  "company": "Zomato",
  "website": "zomato.com",
  "role": "Head of Operations",
  "message": "We spend too much time on manual reporting"
}
```

Response:

```json
{
  "success": true,
  "message": "Thanks Priya! We're preparing your personalized audit report..."
}
```

### `GET /health`

```json
{ "status": "ok", "service": "LeadFlow AI" }
```

---

## Design Decisions & Tradeoffs

### Enrichment pipeline

- Primary: direct website scrape using `requests` + `BeautifulSoup`.
- Fallback: Google search scrape when the website is thin or JS-heavy.
- Synthesis: Gemini processes raw text into structured JSON with industry, pain points, automation opportunities, and tech signals.
- Tradeoff: No Selenium/Playwright. JS-heavy sites may return limited data, but the Google fallback recovers useful signals.

### PDF generation

- `pdfkit` with `wkhtmltopdf` renders an HTML + CSS Jinja2 template into the final PDF.
- Tradeoff: `wkhtmltopdf` must be installed separately, but avoids heavyweight browser dependencies.

### Email delivery

- Gmail SMTP with the PDF attached via standard MIME helpers.
- Tradeoff: no dedicated email queue or retry system. For production, a background job system would be safer.

### Background processing

- `/submit` returns immediately for better UX.
- The full pipeline runs in a `ThreadPoolExecutor` via FastAPI background tasks.

### Error handling

- Each stage has its own try/catch boundary.
- If scraping fails completely, Gemini still generates the best report it can from the company name and website alone.

---

## Limitations

- JS-heavy SPAs may not scrape well, though the Google fallback helps.
- Google search scraping is fragile and could break if Google changes its HTML structure.
- `wkhtmltopdf` must be installed separately for PDF generation.
- Gmail sending requires 2-Step Verification and an App Password.
- No email queue or retry system yet.
