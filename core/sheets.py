import gspread
from google.oauth2.service_account import Credentials
import aiohttp
import logging
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

LEADS_HEADERS = [
    'Company Name', 'Website', 'Phone', 'Email', 'Contact Name',
    'City', 'Address', 'Country', 'Business Type',
    'Google Rating', 'Google Reviews',
    'Lead Score', 'Urgency', 'Deal Size', 'Scored By',
    'Service Opportunity', 'Gaps Found', 'Reasoning', 'Recommended Pitch',
    'Has WhatsApp', 'Has Booking', 'Has SSL', 'Mobile Optimized',
    'Has Payment', 'Has Chatbot', 'Has Contact Form',
    'Tech Stack', 'Copyright Year',
    'Source', 'Date Added'
]

ERRORS_HEADERS = ['Timestamp', 'Error', 'Node', 'Lead Info']


def get_sheets_client(service_account_json: str):
    """Initialize gspread client from service account JSON string"""
    try:
        creds_dict = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Sheets auth failed: {e}")
        return None


def ensure_sheet_headers(worksheet, headers: list):
    """Make sure headers exist in row 1 — NEVER deletes existing data"""
    try:
        existing = worksheet.row_values(1)
        if not existing:
            # Sheet is empty — safe to add headers
            worksheet.insert_row(headers, index=1, value_input_option='RAW')
        # If headers already exist (even partially), leave everything as-is
    except Exception as e:
        logger.error(f"Header setup error: {e}")


def get_existing_leads(worksheet) -> set:
    """Get set of (company_name, phone) tuples for dedup"""
    try:
        records = worksheet.get_all_values()
        if len(records) < 2:
            return set()
        seen = set()
        for row in records[1:]:
            if len(row) >= 3:
                name = row[0].strip().lower()
                phone = row[2].strip()
                seen.add((name, phone))
        return seen
    except Exception as e:
        logger.error(f"Dedup fetch error: {e}")
        return set()


def lead_to_row(lead: dict) -> list:
    """Convert lead dict to sheet row"""
    return [
        lead.get('company_name', ''),
        lead.get('website') or lead.get('raw_url', ''),
        lead.get('phone', ''),
        lead.get('email', ''),
        '' if (lead.get('contact_name') or '').strip() in ('', 'None None') else lead.get('contact_name', ''),
        lead.get('city', ''),
        lead.get('address', ''),
        lead.get('country', 'India'),
        lead.get('business_type', ''),
        lead.get('google_rating', ''),
        lead.get('google_reviews', 0),
        lead.get('lead_score', 0),
        lead.get('urgency', ''),
        lead.get('estimated_deal_size', ''),
        lead.get('scored_by', ''),
        lead.get('service_opportunity', ''),
        lead.get('gaps_found', ''),
        lead.get('reasoning', ''),
        lead.get('recommended_pitch', ''),
        '✓' if lead.get('has_whatsapp') else '✗',
        '✓' if lead.get('has_booking_form') else '✗',
        '✓' if lead.get('has_ssl') else '✗',
        '✓' if lead.get('has_mobile_viewport') else '✗',
        '✓' if lead.get('has_online_payment') else '✗',
        '✓' if lead.get('has_chatbot') else '✗',
        '✓' if lead.get('has_contact_form') else '✗',
        ', '.join(lead.get('tech_stack_detected', [])),
        lead.get('copyright_year', ''),
        lead.get('source', 'GoogleMaps'),
        datetime.now().strftime('%Y-%m-%d %H:%M'),
    ]


def save_leads_to_sheet(gc, sheet_id: str, leads: list) -> dict:
    """Save qualified leads to Google Sheets, dedup by name+phone"""
    stats = {'saved': 0, 'skipped_dup': 0, 'errors': 0}
    try:
        sh = gc.open_by_key(sheet_id)

        # Get or create Leads tab
        try:
            ws = sh.worksheet('Leads')
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet('Leads', rows=1000, cols=30)

        ensure_sheet_headers(ws, LEADS_HEADERS)
        existing = get_existing_leads(ws)

        rows_to_add = []
        for lead in leads:
            name_key = lead.get('company_name', '').strip().lower()
            phone = lead.get('phone', '').strip()
            if (name_key, phone) in existing:
                stats['skipped_dup'] += 1
                continue
            existing.add((name_key, phone))
            rows_to_add.append(lead_to_row(lead))

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option='RAW')
            stats['saved'] = len(rows_to_add)

    except Exception as e:
        logger.error(f"Sheet save error: {e}")
        stats['errors'] += 1

    return stats


def log_error_to_sheet(gc, sheet_id: str, error: str, node: str, lead_info: str = ''):
    """Log errors to Errors tab"""
    try:
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet('Errors')
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet('Errors', rows=200, cols=4)
        ensure_sheet_headers(ws, ERRORS_HEADERS)
        ws.append_row([datetime.now().isoformat(), error, node, lead_info])
    except Exception as e:
        logger.error(f"Error logging failed: {e}")


# ─────────────────────────────────────────────
# HUNTER.IO EMAIL LOOKUP
# ─────────────────────────────────────────────

async def lookup_email_hunter(session: aiohttp.ClientSession, domain: str, api_key: str) -> dict:
    """Look up email via Hunter.io domain search"""
    if not domain or not api_key:
        return {}
    try:
        params = {'domain': domain, 'api_key': api_key, 'limit': 3}
        async with session.get('https://api.hunter.io/v2/domain-search',
                                params=params,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                emails = data.get('data', {}).get('emails', [])
                if emails:
                    best = emails[0]
                    return {
                        'email': best.get('value', ''),
                        'contact_name': f"{best.get('first_name', '')} {best.get('last_name', '')}".strip(),
                    }
    except Exception as e:
        logger.debug(f"Hunter lookup failed for {domain}: {e}")
    return {}