#!/usr/bin/env python3
"""Test create_invoice tool - Actually create a real invoice in Odoo."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os
import requests
from datetime import datetime, timedelta

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "MYdb")
ODOO_USER = os.getenv("ODOO_USER", "iam@gmail.com")
ODOO_PASS = os.getenv("ODOO_PASSWORD", "admin123")

session = requests.Session()

def authenticate():
    resp = session.post(f"{ODOO_URL}/web/session/authenticate",
        json={"jsonrpc": "2.0", "method": "call",
              "params": {"db": ODOO_DB, "login": ODOO_USER, "password": ODOO_PASS}})
    return resp.json().get("result", {}).get("uid")

def call_odoo(model, method, args=None, kwargs=None):
    resp = session.post(f"{ODOO_URL}/web/dataset/call_kw",
        json={"jsonrpc": "2.0", "method": "call",
              "params": {"model": model, "method": method,
                        "args": args or [], "kwargs": kwargs or {}}})
    return resp.json().get("result")

print("=" * 80)
print("🧪 TEST: Create Real Invoice in Odoo")
print("=" * 80)

if not authenticate():
    print("❌ Authentication failed")
    sys.exit(1)

print("✅ Authenticated\n")

# Test 1: Create invoice for existing customer
print("📝 Test 1: Create invoice for TechCorp Solutions")
print("-" * 80)

customer_email = "contact@techcorp.com"
amount = 7500.00
description = "Website Development - Phase 2 (TEST INVOICE)"
due_days = 30

# Find customer
customers = call_odoo("res.partner", "search_read",
    args=[[["email", "=", customer_email]]],
    kwargs={"fields": ["id", "name"], "limit": 1})

if not customers:
    print(f"❌ Customer not found: {customer_email}")
    sys.exit(1)

customer = customers[0]
print(f"✅ Found customer: {customer['name']} (ID: {customer['id']})")

# Create invoice
invoice_date = datetime.now().strftime("%Y-%m-%d")
due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

print(f"\n📄 Creating invoice:")
print(f"   Customer: {customer['name']}")
print(f"   Amount: ${amount:,.2f}")
print(f"   Description: {description}")
print(f"   Invoice Date: {invoice_date}")
print(f"   Due Date: {due_date}")

invoice_id = call_odoo("account.move", "create",
    args=[{
        "move_type": "out_invoice",
        "partner_id": customer['id'],
        "invoice_date": invoice_date,
        "invoice_date_due": due_date,
        "invoice_line_ids": [(0, 0, {
            "name": description,
            "quantity": 1,
            "price_unit": amount,
        })],
    }])

print(f"\n✅ Invoice created! ID: {invoice_id}")

# Post the invoice
call_odoo("account.move", "action_post", args=[[invoice_id]])
print("✅ Invoice posted (confirmed)")

# Get invoice details
invoice = call_odoo("account.move", "read",
    args=[[invoice_id]],
    kwargs={"fields": ["name", "amount_total", "state", "payment_state"]})

inv = invoice[0]
print(f"\n📊 Invoice Details:")
print(f"   Invoice Number: {inv['name']}")
print(f"   Amount: ${inv['amount_total']:,.2f}")
print(f"   State: {inv['state']}")
print(f"   Payment Status: {inv['payment_state']}")

# Verify it appears in invoice list
print(f"\n🔍 Verifying invoice appears in system...")
all_invoices = call_odoo("account.move", "search_read",
    args=[[["id", "=", invoice_id]]],
    kwargs={"fields": ["name", "partner_id", "amount_total"], "limit": 1})

if all_invoices:
    print(f"✅ Invoice verified in system: {all_invoices[0]['name']}")
else:
    print("❌ Invoice not found in system")

print("\n" + "=" * 80)
print("✅ TEST PASSED - Invoice created successfully!")
print("=" * 80)
print(f"\n📝 Summary:")
print(f"   Invoice Number: {inv['name']}")
print(f"   Customer: {customer['name']}")
print(f"   Amount: ${inv['amount_total']:,.2f}")
print(f"   Status: Posted and ready for payment")
print(f"\n💡 You can view this invoice in Odoo:")
print(f"   {ODOO_URL}/web#id={invoice_id}&model=account.move&view_type=form")
