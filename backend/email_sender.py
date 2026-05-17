import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _build_email_body(first_name: str, company_name: str, drive_link: str, from_email: str) -> tuple[str, str]:
    drive_section = ""
    if drive_link:
        drive_section = f"""
        <p style="margin: 16px 0;">
            You can also
            <a href="{drive_link}" style="color: #6366f1; font-weight: 600;">view the report online</a>
            anytime.
        </p>"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f8f9fa; margin: 0; padding: 0; }}
            .wrapper {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); padding: 40px 48px; }}
            .header h1 {{ color: white; margin: 0; font-size: 24px; font-weight: 700; }}
            .header p {{ color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 14px; }}
            .body {{ padding: 40px 48px; color: #374151; line-height: 1.7; }}
            .body h2 {{ color: #1f2937; font-size: 20px; margin: 0 0 16px; }}
            .body p {{ margin: 0 0 16px; font-size: 15px; }}
            .highlight-box {{ background: #f0f0ff; border-left: 4px solid #6366f1; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 24px 0; }}
            .highlight-box p {{ margin: 0; font-size: 14px; color: #4338ca; }}
            .cta-button {{ display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px; margin: 8px 0; }}
            .footer {{ background: #f9fafb; padding: 24px 48px; border-top: 1px solid #e5e7eb; }}
            .footer p {{ color: #9ca3af; font-size: 13px; margin: 0; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="header">
                <h1>SimplifIQ</h1>
                <p>AI Automation · Business Intelligence</p>
            </div>
            <div class="body">
                <h2>Hi {first_name},</h2>
                <p>
                    Thank you for reaching out to SimplifIQ. We've prepared a personalized
                    <strong>AI Automation Audit Report</strong> for <strong>{company_name}</strong> —
                    attached to this email.
                </p>
                <div class="highlight-box">
                    <p>
                        📊 The report includes a detailed analysis of automation opportunities
                        specific to {company_name}'s operations, estimated impact, and recommended
                        next steps to get started.
                    </p>
                </div>
                <p>
                    The audit was prepared based on publicly available information about your
                    company. We'd love to walk you through the findings and discuss how
                    SimplifIQ can specifically help your team.
                </p>
                {drive_section}
                <p>
                    <a href="mailto:{from_email}" class="cta-button">Reply to Schedule a Call →</a>
                </p>
                <p style="margin-top: 24px; color: #6b7280; font-size: 14px;">
                    We typically respond within a few hours during business days.
                </p>
            </div>
            <div class="footer">
                <p>SimplifIQ · AI Automation for Modern Businesses</p>
                <p style="margin-top: 4px;">You're receiving this because you submitted a contact form on our website.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""Hi {first_name},

Thank you for reaching out to SimplifIQ. We've prepared a personalized AI Automation Audit Report for {company_name}, attached to this email.

The report includes:
- Company overview and operational analysis
- Identified automation opportunities specific to your business
- Estimated impact and implementation complexity
- Recommended next steps

We'd love to walk you through the findings. Just reply to this email to schedule a call.

Best,
The SimplifIQ Team
"""

    return text_body, html_body


def send_report_email(
    to_email: str,
    to_name: str,
    company_name: str,
    pdf_path: str,
    drive_link: str = ""
) -> bool:
    """Send the audit report PDF to the prospect via Gmail SMTP."""

    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        print("[Email] Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD")
        return False

    first_name = to_name.split()[0] if to_name else "there"
    text_body, html_body = _build_email_body(first_name, company_name, drive_link, gmail_address)

    message = MIMEMultipart("mixed")
    message["From"] = gmail_address
    message["To"] = to_email
    message["Subject"] = f"Your AI Automation Audit Report — {company_name} | SimplifIQ"

    alternative_part = MIMEMultipart("alternative")
    alternative_part.attach(MIMEText(text_body, "plain", "utf-8"))
    alternative_part.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alternative_part)

    with open(pdf_path, "rb") as f:
        attachment = MIMEBase("application", "pdf")
        attachment.set_payload(f.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"SimplifIQ_Audit_{company_name.replace(' ', '_')}.pdf",
    )
    message.attach(attachment)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, [to_email], message.as_string())

        print(f"[Email] Sent to {to_email} via Gmail SMTP")
        return True
    except Exception as e:
        print(f"[Email] Failed: {e}")
        return False
