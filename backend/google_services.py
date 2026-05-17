import os
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_credentials():
    """Load service account credentials from a JSON file."""
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    with open(creds_path) as f:
        info = json.load(f)
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def append_lead_to_sheet(
    name: str,
    email: str,
    company: str,
    website: str,
    report_status: str,
    drive_link: str = "",
) -> bool:
    """Append a new lead row to the Google Sheet tracker."""
    if not os.getenv("GOOGLE_SHEET_ID"):
        return False
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    try:
        creds = _get_credentials()
        service = build("sheets", "v4", credentials=creds)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [[name, email, company, website, timestamp, report_status, drive_link]]

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sheet1!A:G",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        ).execute()

        print(f"[Sheets] Lead logged for {company}")
        return True

    except Exception as e:
        print(f"[Sheets] Error: {e}")
        return False


def ensure_sheet_headers(sheet_id: str) -> None:
    """One-time setup: add headers to the sheet if it's empty."""
    try:
        creds = _get_credentials()
        service = build("sheets", "v4", credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="Sheet1!A1:G1"
        ).execute()

        if not result.get("values"):
            headers = [["Name", "Email", "Company", "Website", "Timestamp", "Report Status", "Drive Link"]]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Sheet1!A1:G1",
                valueInputOption="RAW",
                body={"values": headers},
            ).execute()
            print("[Sheets] Headers added")
    except Exception as e:
        print(f"[Sheets] Header setup error: {e}")


def upload_pdf_to_drive(pdf_path: str, company_name: str) -> str:
    """Upload PDF to a Google Drive folder and return shareable link."""
    if not os.getenv("GOOGLE_DRIVE_FOLDER_ID"):
        return ""
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    try:
        creds = _get_credentials()
        service = build("drive", "v3", credentials=creds)

        filename = f"SimplifIQ_Audit_{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=True)

        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        # Make it viewable by anyone with the link
        service.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = uploaded.get("webViewLink", "")
        print(f"[Drive] Uploaded: {filename} → {link}")
        return link

    except Exception as e:
        print(f"[Drive] Error: {e}")
        return ""
