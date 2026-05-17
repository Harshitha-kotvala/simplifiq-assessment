import os
import json
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pdfkit
import google.generativeai as genai
import tempfile

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def generate_report_content(intelligence: dict) -> dict:
    """Use Gemini to write the full personalized report narrative."""

    prompt = f"""You are a senior consultant at SimplifIQ, an AI automation company. 
A prospect has submitted their details and you need to write a highly personalized audit report for them.

Company Intelligence:
{json.dumps(intelligence, indent=2)}

Write a professional audit report. Return ONLY valid JSON (no markdown fences) with these exact keys:

{{
  "executive_summary": "3-4 sentences. Acknowledge who they are, what they do, and why AI automation is relevant to them specifically. Sound like you researched them.",
  
  "company_overview": "4-5 sentences covering their business model, market position, and what makes them interesting. Reference specific details from the intelligence.",
  
  "current_landscape_analysis": "4-5 sentences about the typical operational challenges companies in their space face. Make it feel specific to their industry and size.",
  
  "pain_points": [
    {{"title": "Pain Point 1 Title", "description": "2-3 sentence explanation of this specific challenge for their type of business"}},
    {{"title": "Pain Point 2 Title", "description": "2-3 sentence explanation"}},
    {{"title": "Pain Point 3 Title", "description": "2-3 sentence explanation"}}
  ],
  
  "automation_opportunities": [
    {{
      "title": "Opportunity 1 Title",
      "description": "2-3 sentences on what can be automated",
      "impact": "Expected business impact (time saved, cost reduced, conversion improved etc)",
      "complexity": "Low / Medium / High"
    }},
    {{
      "title": "Opportunity 2 Title", 
      "description": "2-3 sentences",
      "impact": "...",
      "complexity": "Low / Medium / High"
    }},
    {{
      "title": "Opportunity 3 Title",
      "description": "2-3 sentences",
      "impact": "...",
      "complexity": "Low / Medium / High"
    }}
  ],
  
  "simplyfiq_fit": "3-4 sentences on specifically how SimplifIQ's AI automation services align with this company's needs. Sound like a consultant, not a salesperson.",
  
  "recommended_next_steps": [
    "Step 1: specific action",
    "Step 2: specific action", 
    "Step 3: specific action"
  ],
  
  "closing_note": "2 sentences. Warm, professional close that invites them to a conversation. Personalize to their company."
}}"""

    response = model.generate_content(prompt)

    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


def generate_pdf(intelligence: dict, output_path: str) -> str:
    """Generate a styled PDF report from company intelligence."""

    print(f"[Report] Generating report content via Gemini...")
    content = generate_report_content(intelligence)
    print(f"[Report] Content generated. Rendering PDF...")

    # Merge intelligence + content for template
    template_data = {
        **intelligence,
        **content,
        "generated_date": datetime.now().strftime("%B %d, %Y"),
        "generated_time": datetime.now().strftime("%I:%M %p"),
        "report_id": f"SIQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "contact_first_name": (intelligence.get("contact_name", "").split()[0]
                               if intelligence.get("contact_name") else "there"),
    }

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("report_template.html")
    html_content = template.render(**template_data)

    # Render to PDF
    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdfkit.from_string(html_content, output_path, configuration=config)
    print(f"[Report] PDF saved to {output_path}")
    return output_path
