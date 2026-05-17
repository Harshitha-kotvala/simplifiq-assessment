from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from dotenv import load_dotenv
import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

from enrichment import enrich_company
from report import generate_pdf
from email_sender import send_report_email
from google_services import append_lead_to_sheet, upload_pdf_to_drive, ensure_sheet_headers

app = FastAPI(title="SimplifIQ Lead Automation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=4)


class LeadSubmission(BaseModel):
    name: str
    email: EmailStr
    company: str
    website: str
    role: str = ""
    message: str = ""

    @field_validator("website")
    @classmethod
    def normalize_website(cls, v):
        v = v.strip()
        if not v.startswith("http"):
            v = "https://" + v
        return v

    @field_validator("name", "company")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


def run_full_pipeline(lead: LeadSubmission):
    """
    The full automation pipeline — runs in a background thread.
    1. Enrich company data
    2. Generate PDF report
    3. Upload to Drive
    4. Send email
    5. Log to Sheets
    """
    print(f"\n{'='*50}")
    print(f"[Pipeline] Starting for {lead.company} ({lead.email})")
    print(f"{'='*50}")

    report_status = "failed"
    drive_link = ""
    pdf_path = ""

    try:
        # Step 1: Enrich
        intelligence = enrich_company(lead.company, lead.website, lead.name)

        # Step 2: Generate PDF
        pdf_filename = f"report_{lead.company.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        generate_pdf(intelligence, pdf_path)
        report_status = "generated"

        # Step 3: Upload to Drive (bonus)
        drive_link = upload_pdf_to_drive(pdf_path, lead.company)

        # Step 4: Send email
        email_sent = send_report_email(
            to_email=lead.email,
            to_name=lead.name,
            company_name=lead.company,
            pdf_path=pdf_path,
            drive_link=drive_link,
        )
        report_status = "sent" if email_sent else "email_failed"

    except Exception as e:
        print(f"[Pipeline] ERROR: {e}")
        report_status = f"error: {str(e)[:100]}"

    finally:
        # Step 5: Log to Sheets (bonus) — always log even on failure
        append_lead_to_sheet(
            name=lead.name,
            email=lead.email,
            company=lead.company,
            website=lead.website,
            report_status=report_status,
            drive_link=drive_link,
        )
        print(f"[Pipeline] Done. Status: {report_status}")


@app.on_event("startup")
async def startup_event():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, ensure_sheet_headers, sheet_id)


@app.post("/submit")
async def submit_lead(lead: LeadSubmission, background_tasks: BackgroundTasks):
    """
    Accepts lead form submission and kicks off the full automation pipeline.
    Returns immediately — pipeline runs in background.
    """
    background_tasks.add_task(
        lambda: executor.submit(run_full_pipeline, lead)
    )

    return {
        "success": True,
        "message": f"Thanks {lead.name.split()[0]}! We're preparing your personalized audit report and will email it to {lead.email} within a few minutes.",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SimplifIQ Lead Automation"}


# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
