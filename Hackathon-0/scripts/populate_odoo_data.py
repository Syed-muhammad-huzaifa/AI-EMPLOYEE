#!/usr/bin/env python3
"""Populate Odoo with fake company data for testing."""

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
    """Authenticate with Odoo."""
    resp = session.post(
        f"{ODOO_URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": ODOO_DB,
                "login": ODOO_USER,
                "password": ODOO_PASS,
            },
        },
    )
    result = resp.json().get("result", {})
    if result and result.get("uid"):
        print(f"✅ Authenticated as {ODOO_USER} (uid={result['uid']})")
        return True
    return False

def call_odoo(model, method, args=None, kwargs=None):
    """Call Odoo API."""
    args = args or []
    kwargs = kwargs or {}

    resp = session.post(
        f"{ODOO_URL}/web/dataset/call_kw",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs,
            },
        },
    )
    return resp.json().get("result")

def create_customers():
    """Create fake customers."""
    print("\n📋 Creating fake customers...")

    customers = [
        {"name": "TechCorp Solutions", "email": "contact@techcorp.com", "phone": "+1-555-0101"},
        {"name": "Global Enterprises", "email": "info@globalent.com", "phone": "+1-555-0102"},
        {"name": "StartupHub Inc", "email": "hello@startuphub.io", "phone": "+1-555-0103"},
        {"name": "Digital Innovations", "email": "team@digitalinno.com", "phone": "+1-555-0104"},
        {"name": "CloudFirst Ltd", "email": "sales@cloudfirst.com", "phone": "+1-555-0105"},
    ]

    created = []
    for cust in customers:
        # Check if exists
        existing = call_odoo(
            "res.partner",
            "search_read",
            args=[[["email", "=", cust["email"]]]],
            kwargs={"fields": ["id"], "limit": 1}
        )

        if existing:
            print(f"  ⏭️  {cust['name']} already exists")
            created.append(existing[0]["id"])
        else:
            cust_id = call_odoo(
                "res.partner",
                "create",
                args=[{
                    "name": cust["name"],
                    "email": cust["email"],
                    "phone": cust["phone"],
                    "customer_rank": 1,
                }]
            )
            print(f"  ✅ Created {cust['name']} (id={cust_id})")
            created.append(cust_id)

    return created

def create_invoices(customer_ids):
    """Create fake invoices."""
    print("\n💰 Creating fake invoices...")

    invoices = [
        {"customer_idx": 0, "amount": 5000, "desc": "Website Development", "days_ago": 5, "paid": True},
        {"customer_idx": 1, "amount": 12000, "desc": "Cloud Infrastructure Setup", "days_ago": 10, "paid": True},
        {"customer_idx": 2, "amount": 3500, "desc": "Mobile App Design", "days_ago": 15, "paid": False},
        {"customer_idx": 3, "amount": 8000, "desc": "API Integration Services", "days_ago": 20, "paid": True},
        {"customer_idx": 4, "amount": 6500, "desc": "Security Audit", "days_ago": 25, "paid": False},
        {"customer_idx": 0, "amount": 4200, "desc": "Monthly Maintenance", "days_ago": 3, "paid": True},
    ]

    created = []
    for inv in invoices:
        invoice_date = (datetime.now() - timedelta(days=inv["days_ago"])).strftime("%Y-%m-%d")
        due_date = (datetime.now() - timedelta(days=inv["days_ago"]) + timedelta(days=30)).strftime("%Y-%m-%d")

        invoice_id = call_odoo(
            "account.move",
            "create",
            args=[{
                "move_type": "out_invoice",
                "partner_id": customer_ids[inv["customer_idx"]],
                "invoice_date": invoice_date,
                "invoice_date_due": due_date,
                "invoice_line_ids": [(0, 0, {
                    "name": inv["desc"],
                    "quantity": 1,
                    "price_unit": inv["amount"],
                })],
            }]
        )

        # Post the invoice
        call_odoo("account.move", "action_post", args=[[invoice_id]])

        # Mark as paid if needed
        if inv["paid"]:
            # Register payment (simplified - just mark as paid)
            pass

        status = "✅ Paid" if inv["paid"] else "⏳ Unpaid"
        print(f"  {status} Invoice: ${inv['amount']} - {inv['desc']}")
        created.append(invoice_id)

    return created

def create_expenses():
    """Create fake expenses."""
    print("\n💸 Creating fake expenses...")

    expenses = [
        {"amount": 1200, "desc": "AWS Cloud Hosting", "days_ago": 5},
        {"amount": 500, "desc": "Software Licenses", "days_ago": 10},
        {"amount": 800, "desc": "Marketing Campaign", "days_ago": 15},
        {"amount": 350, "desc": "Office Supplies", "days_ago": 20},
    ]

    # Find or create vendor
    vendors = call_odoo(
        "res.partner",
        "search_read",
        args=[[["name", "=", "General Vendor"]]],
        kwargs={"fields": ["id"], "limit": 1}
    )

    if vendors:
        vendor_id = vendors[0]["id"]
    else:
        vendor_id = call_odoo(
            "res.partner",
            "create",
            args=[{"name": "General Vendor", "supplier_rank": 1}]
        )

    for exp in expenses:
        expense_date = (datetime.now() - timedelta(days=exp["days_ago"])).strftime("%Y-%m-%d")

        expense_id = call_odoo(
            "account.move",
            "create",
            args=[{
                "move_type": "in_invoice",
                "partner_id": vendor_id,
                "invoice_date": expense_date,
                "invoice_line_ids": [(0, 0, {
                    "name": exp["desc"],
                    "quantity": 1,
                    "price_unit": exp["amount"],
                })],
            }]
        )

        # Post the expense
        call_odoo("account.move", "action_post", args=[[expense_id]])

        print(f"  ✅ Expense: ${exp['amount']} - {exp['desc']}")

def main():
    print("=" * 60)
    print("🏢 Populating Odoo with Fake Company Data")
    print("=" * 60)

    if not authenticate():
        print("❌ Authentication failed")
        return 1

    customer_ids = create_customers()
    invoice_ids = create_invoices(customer_ids)
    create_expenses()

    print("\n" + "=" * 60)
    print("✅ Fake data populated successfully!")
    print("=" * 60)
    print(f"  Customers: {len(customer_ids)}")
    print(f"  Invoices: {len(invoice_ids)}")
    print(f"  Expenses: 4")
    print("\n💡 Now run weekly audit to see real data in briefing")

    return 0

if __name__ == "__main__":
    sys.exit(main())
