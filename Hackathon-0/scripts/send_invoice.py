#!/usr/bin/env python3
"""
END-TO-END INVOICE WORKFLOW
===========================
Task: Client needs $200 invoice → hafizsyedhuzaifa5@gmail.com

Steps:
  1. Create / find customer in Odoo
  2. Create $200 invoice and post it
  3. Download PDF from Odoo
  4. Send email with PDF attached via Gmail API

Run: python send_invoice_to_client.py
"""

import os
import sys
import base64
import pickle
import requests
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

ODOO_URL  = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB   = os.getenv("ODOO_DB",  "MYdb")
ODOO_USER = os.getenv("ODOO_USER", "iam@gmail.com")
ODOO_PASS = os.getenv("ODOO_PASSWORD", "admin123")

TOKEN_PATH = BASE_DIR / "config" / "gmail_token.pickle"

CLIENT_EMAIL = "hafizsyedhuzaifa5@gmail.com"
CLIENT_NAME  = "Hafiz Syed Huzaifa"
AMOUNT       = 200.00
DESCRIPTION  = "Professional Services - February 2026"
DUE_DAYS     = 30

# ── Odoo helpers ──────────────────────────────────────────────────────────────

session = requests.Session()

def odoo_auth():
    r = session.post(f"{ODOO_URL}/web/session/authenticate", json={
        "jsonrpc": "2.0", "method": "call",
        "params": {"db": ODOO_DB, "login": ODOO_USER, "password": ODOO_PASS}
    })
    uid = r.json().get("result", {}).get("uid")
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    return uid

def odoo(model, method, args=None, kwargs=None):
    r = session.post(f"{ODOO_URL}/web/dataset/call_kw", json={
        "jsonrpc": "2.0", "method": "call",
        "params": {"model": model, "method": method,
                   "args": args or [], "kwargs": kwargs or {}}
    })
    result = r.json()
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("result")

# ── Gmail helper ──────────────────────────────────────────────────────────────

def gmail_service():
    with open(TOKEN_PATH, "rb") as fh:
        creds = pickle.load(fh)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as fh:
            pickle.dump(creds, fh)
    return build("gmail", "v1", credentials=creds)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("📋 TASK: Send $200 Invoice to hafizsyedhuzaifa5@gmail.com")
    print("=" * 70)

    # ── STEP 1: Authenticate Odoo ─────────────────────────────────────────────
    print("\n[1/5] Connecting to Odoo...")
    odoo_auth()
    print("      ✅ Connected")

    # ── STEP 2: Find or create customer ──────────────────────────────────────
    print(f"\n[2/5] Finding/creating customer ({CLIENT_EMAIL})...")

    partners = odoo("res.partner", "search_read",
        args=[[["email", "=", CLIENT_EMAIL]]],
        kwargs={"fields": ["id", "name", "email"], "limit": 1})

    if partners:
        partner_id = partners[0]["id"]
        print(f"      ✅ Found existing customer: {partners[0]['name']} (ID {partner_id})")
    else:
        partner_id = odoo("res.partner", "create", args=[{
            "name":          CLIENT_NAME,
            "email":         CLIENT_EMAIL,
            "customer_rank": 1,
        }])
        print(f"      ✅ Created new customer: {CLIENT_NAME} (ID {partner_id})")

    # ── STEP 3: Create and post invoice ──────────────────────────────────────
    print(f"\n[3/5] Creating invoice (${AMOUNT:.2f})...")

    invoice_date = datetime.now().strftime("%Y-%m-%d")
    due_date     = (datetime.now() + timedelta(days=DUE_DAYS)).strftime("%Y-%m-%d")

    invoice_id = odoo("account.move", "create", args=[{
        "move_type":          "out_invoice",
        "partner_id":         partner_id,
        "invoice_date":       invoice_date,
        "invoice_date_due":   due_date,
        "invoice_line_ids":   [(0, 0, {
            "name":       DESCRIPTION,
            "quantity":   1,
            "price_unit": AMOUNT,
        })],
    }])

    # Post (confirm) the invoice so it gets a real number
    odoo("account.move", "action_post", args=[[invoice_id]])

    inv = odoo("account.move", "read",
        args=[[invoice_id]],
        kwargs={"fields": ["name", "amount_total", "state"]})[0]

    invoice_number = inv["name"]
    print(f"      ✅ Invoice posted: {invoice_number}  |  ${inv['amount_total']:.2f}  |  {inv['state']}")

    # ── STEP 4: Download PDF ──────────────────────────────────────────────────
    print(f"\n[4/5] Generating PDF...")

    pdf_url  = f"{ODOO_URL}/report/pdf/account.report_invoice/{invoice_id}"
    pdf_resp = session.get(pdf_url)
    pdf_resp.raise_for_status()
    pdf_bytes = pdf_resp.content

    if not pdf_bytes:
        raise RuntimeError("PDF endpoint returned empty content")

    pdf_filename = f"{invoice_number.replace('/', '_')}.pdf"
    pdf_path     = BASE_DIR / pdf_filename
    pdf_path.write_bytes(pdf_bytes)

    print(f"      ✅ PDF: {pdf_filename}  ({len(pdf_bytes)/1024:.1f} KB)")

    # ── STEP 5: Send email with PDF attachment ────────────────────────────────
    print(f"\n[5/5] Sending email to {CLIENT_EMAIL}...")

    subject = f"Invoice {invoice_number} – ${AMOUNT:.2f} due {due_date}"

    body = f"""\
Dear {CLIENT_NAME},

Thank you for working with us! Please find your invoice attached.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Invoice Number : {invoice_number}
Amount Due     : ${AMOUNT:.2f}
Invoice Date   : {invoice_date}
Due Date       : {due_date}
Description    : {DESCRIPTION}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please arrange payment by {due_date}.

If you have any questions, please reply to this email.

Best regards,
AI Employee – Finance Automation
"""

    # Build MIME message with PDF attachment
    msg = MIMEMultipart()
    msg["to"]      = CLIENT_EMAIL
    msg["subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    part = MIMEBase("application", "pdf")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    svc    = gmail_service()
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()

    print(f"      ✅ Email sent!  Gmail message ID: {result['id']}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("✅  WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"  Invoice    : {invoice_number}")
    print(f"  Amount     : ${AMOUNT:.2f}")
    print(f"  Customer   : {CLIENT_NAME} <{CLIENT_EMAIL}>")
    print(f"  Due Date   : {due_date}")
    print(f"  PDF        : {pdf_filename} ({len(pdf_bytes)/1024:.1f} KB)")
    print(f"  Gmail ID   : {result['id']}")
    print()
    print(f"  📬 Check inbox: {CLIENT_EMAIL}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n❌ ERROR: {exc}")
        raise
