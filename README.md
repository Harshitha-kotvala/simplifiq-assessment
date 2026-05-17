# SimplifIQ - AI Lead Automation System

A fully automated lead intake pipeline: form submission -> company research -> personalized PDF audit -> email delivery -> Google Sheets/Drive logging.

---

## What It Does

When a prospect submits the form:

1. Validates the submission with Pydantic.
2. Enriches company data by scraping the website, running a Google fallback search, and synthesizing intelligence with Gemini.
3. Generates a personalized PDF audit report with Gemini + Jinja2 + pdfkit.
4. Uploads the PDF to Google Drive.
5. Emails the report via Gmail SMTP with the PDF attached.
6. Logs the lead to Google Sheets with name, email, company, status, and Drive link.

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
                                 |
                            google_services.py
                           Drive upload + Sheets append
```

---

## Project Structure

```text
simplifiq/
|-- backend/
|   |-- main.py              # FastAPI app, /submit endpoint
|   |-- enrichment.py        # Web scraping + Gemini synthesis
|   |-- report.py            # Report content generation + PDF rendering
|   |-- email_sender.py      # Gmail SMTP email with PDF attachment
|   |-- google_services.py   # Google Sheets + Drive integration
|   `-- requirements.txt
|-- frontend/
|   `-- index.html           # Lead capture form
|-- templates/
|   `-- report_template.html # Jinja2 + pdfkit HTML-to-PDF template
|-- output/                  # Generated PDFs (auto-created)
|-- .env.example
`-- README.md
```

---

## Setup

### 1. Clone & Install

```bash
git clone <repo>
cd simplifiq/backend
pip install -r requirements.txt
```

### 2. Install wkhtmltopdf

`pdfkit` uses `wkhtmltopdf` under the hood, so install it separately.

- Download the Windows installer from https://wkhtmltopdf.org/downloads.html
- Install it and make sure `wkhtmltopdf.exe` is available on your PATH

If you prefer, you can also configure the executable path directly in code or environment variables.

### 3. Configure Environment

```bash
cp .env.example .env
# Fill in all values in .env
```

Required:

- `GEMINI_API_KEY` - Gemini API key
- `GMAIL_ADDRESS` - Gmail address used to send the report
- `GMAIL_APP_PASSWORD` - Gmail App Password for SMTP login

Bonus (Sheets + Drive):

- `GOOGLE_SERVICE_ACCOUNT_FILE` - path to the service account JSON file
- `GOOGLE_SHEET_ID` - ID from sheet URL: `docs.google.com/spreadsheets/d/{SHEET_ID}/`
- `GOOGLE_DRIVE_FOLDER_ID` - ID from folder URL: `drive.google.com/drive/folders/{FOLDER_ID}`

### 4. Google Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project, then enable the Google Sheets API and Google Drive API
3. Create a service account and download the JSON key
4. Save the downloaded JSON key somewhere in the project, then set `GOOGLE_SERVICE_ACCOUNT_FILE` in `.env` to that file path
5. Share your Google Sheet with the service account email as Editor
6. Share your Drive folder with the same email as Editor

### 5. Gmail App Password Setup

1. Go to https://myaccount.google.com/ and open Security
2. Enable 2-Step Verification first
3. Then open https://myaccount.google.com/apppasswords
4. Create an app password named `SimplifIQ`
5. Copy the 16-character password and paste it into `GMAIL_APP_PASSWORD`

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
{ "status": "ok", "service": "SimplifIQ Lead Automation" }
```

---

## Design Decisions & Tradeoffs

### Enrichment pipeline

- Primary: direct website scrape using `requests` + `BeautifulSoup`.
- Fallback: Google search scrape when the website is thin or JS-heavy.
- Synthesis: Gemini processes raw text into structured JSON with industry, pain points, automation opportunities, tech signals, and more.
- Tradeoff: No Selenium/Playwright. JS-heavy sites may return limited data, but the Google fallback helps recover useful signals.

### PDF generation

- `pdfkit` with `wkhtmltopdf` for easier Windows setup.
- `wkhtmltopdf` renders the HTML template into the final PDF.
- The report is still fully styled with HTML + CSS inside Jinja2.

### Email delivery

- Gmail SMTP is used instead of a third-party email provider.
- The PDF is attached using the standard library email MIME helpers.
- Tradeoff: no dedicated email queue or retry system. For production, a background job system would be safer.

### Background processing

- `/submit` returns immediately for better UX.
- The full pipeline runs in a `ThreadPoolExecutor` via FastAPI background tasks.

### Error handling

- Each stage has its own try/catch boundaries.
- The pipeline always logs to Sheets even if later steps fail.
- If scraping fails completely, Gemini still generates the best report it can from the company name and website.

---

## Limitations

- JS-heavy SPAs may not scrape well, though the Google fallback helps.
- Google search scraping is fragile and could break if Google changes its HTML.
- `wkhtmltopdf` must be installed separately for PDF generation.
- Gmail sending requires 2-Step Verification and an App Password.
- No email queue or retry system yet.
- The Google service account must be explicitly shared on both the Sheet and Drive folder.

---

## Bonus Features

- Google Sheets logging: name, email, company, website, timestamp, status, and Drive link.
- Google Drive archiving: PDF uploaded with a shareable link included in the email body.
- Auto-header setup on first run for Sheets.
