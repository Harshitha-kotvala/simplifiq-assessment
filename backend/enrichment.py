import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import json
import re
from urllib.parse import urlparse

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


def safe_scrape(url: str) -> dict:
    """Scrape a company website and extract key text content."""
    try:
        if not url.startswith("http"):
            url = "https://" + url

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            tag.decompose()

        # Pull structured content
        title = soup.title.string.strip() if soup.title else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        # Headings give the clearest signal about what they do
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:15]]

        # Main body paragraphs
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40][:20]

        # Also try about/services pages
        about_text = ""
        about_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if any(kw in a["href"].lower() for kw in ["about", "services", "solutions", "product", "what-we-do"])
        ][:3]

        for link in about_links:
            try:
                if link.startswith("/"):
                    domain = urlparse(url).scheme + "://" + urlparse(url).netloc
                    link = domain + link
                elif not link.startswith("http"):
                    continue
                sub_resp = requests.get(link, headers=headers, timeout=8)
                sub_soup = BeautifulSoup(sub_resp.text, "lxml")
                for tag in sub_soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                about_text += " ".join(
                    p.get_text(strip=True) for p in sub_soup.find_all("p") if len(p.get_text(strip=True)) > 40
                )[:2000]
                break
            except Exception:
                continue

        return {
            "success": True,
            "title": title,
            "meta_description": meta_desc,
            "headings": headings,
            "paragraphs": paragraphs[:10],
            "about_text": about_text[:2000],
            "url": url,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def google_fallback_search(company_name: str) -> str:
    """Fallback: scrape Google search snippet for the company."""
    try:
        query = f"{company_name} company what they do services"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "lxml")
        snippets = [s.get_text(strip=True) for s in soup.find_all("div", class_=re.compile(r"BNeawe|VwiC3b|s3v9rd"))[:5]]
        return " ".join(snippets)[:1500]
    except Exception:
        return ""


def synthesize_with_gemini(company_name: str, website: str, raw_data: dict) -> dict:
    """Use Gemini to turn raw scraped data into structured company intelligence."""

    raw_text = f"""
Company: {company_name}
Website: {website}
Page Title: {raw_data.get('title', '')}
Meta Description: {raw_data.get('meta_description', '')}
Headings: {' | '.join(raw_data.get('headings', []))}
Body Content: {' '.join(raw_data.get('paragraphs', []))}
About/Services Page: {raw_data.get('about_text', '')}
Google Snippet: {raw_data.get('google_snippet', '')}
"""

    prompt = f"""You are a senior business analyst. Based on the raw data below about a company, extract structured intelligence.

{raw_text}

Return ONLY a valid JSON object (no markdown, no explanation) with these exact keys:
{{
  "company_name": "...",
  "industry": "...",
  "what_they_do": "2-3 sentence summary of their core business",
  "target_market": "who their customers are",
  "key_products_services": ["list", "of", "main", "offerings"],
  "tech_signals": ["any technology or tools mentioned or inferred"],
  "company_size_signal": "startup / SMB / mid-market / enterprise (infer from signals)",
  "likely_pain_points": ["3-4 specific operational pain points this type of company faces"],
  "automation_opportunities": ["3-4 specific workflows that could be automated with AI"],
  "recent_signals": "any news, growth signals, or notable activity if found",
  "tone_of_brand": "professional / casual / technical / creative etc",
  "confidence": "high / medium / low based on data quality"
}}"""

    response = model.generate_content(prompt)

    raw_response = response.text.strip()
    # Strip markdown fences if present
    raw_response = re.sub(r"```json|```", "", raw_response).strip()
    return json.loads(raw_response)


def enrich_company(company_name: str, website: str, contact_name: str = "") -> dict:
    """
    Main enrichment pipeline.
    Returns structured company intelligence ready for report generation.
    """
    print(f"[Enrichment] Starting for {company_name} ({website})")

    # Step 1: Scrape website
    scraped = safe_scrape(website)
    print(f"[Enrichment] Scrape {'succeeded' if scraped['success'] else 'failed'}: {scraped.get('error','')}")

    # Step 2: Google fallback if scrape thin
    google_text = ""
    total_content = len(" ".join(scraped.get("paragraphs", [])))
    if not scraped["success"] or total_content < 200:
        print("[Enrichment] Thin data, running Google fallback")
        google_text = google_fallback_search(company_name)

    scraped["google_snippet"] = google_text

    # Step 3: Gemini synthesis
    try:
        intelligence = synthesize_with_gemini(company_name, website, scraped)
        print(f"[Enrichment] Gemini synthesis done. Confidence: {intelligence.get('confidence')}")
    except json.JSONDecodeError:
        # Fallback structure if Gemini returns bad JSON
        print("[Enrichment] Gemini JSON parse failed, using fallback structure")
        intelligence = {
            "company_name": company_name,
            "industry": "Technology",
            "what_they_do": f"{company_name} is a company operating at {website}.",
            "target_market": "Business customers",
            "key_products_services": ["Core product/service"],
            "tech_signals": [],
            "company_size_signal": "unknown",
            "likely_pain_points": [
                "Manual data processing and reporting",
                "Repetitive customer communication workflows",
                "Lack of automation in lead management",
            ],
            "automation_opportunities": [
                "Automated lead follow-up emails",
                "AI-powered report generation",
                "Workflow automation for internal processes",
            ],
            "recent_signals": "No recent data found",
            "tone_of_brand": "professional",
            "confidence": "low",
        }

    intelligence["contact_name"] = contact_name
    intelligence["website"] = website
    return intelligence
