#!/usr/bin/env python3
"""Quick test script for Odoo MCP tools."""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the Odoo client
from dotenv import load_dotenv
load_dotenv()

import requests

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "MYdb")
ODOO_USER = os.getenv("ODOO_USER", "iam@gmail.com")
ODOO_PASS = os.getenv("ODOO_PASSWORD", "admin123")

def test_authentication():
    """Test Odoo authentication."""
    print(f"🔐 Testing authentication to {ODOO_URL}...")
    print(f"   Database: {ODOO_DB}")
    print(f"   User: {ODOO_USER}")

    session = requests.Session()

    try:
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
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})

        if result and result.get("uid"):
            print(f"✅ Authentication successful! UID: {result['uid']}")
            print(f"   Username: {result.get('username', 'N/A')}")
            print(f"   Company: {result.get('company_name', 'N/A')}")
            return True
        else:
            print(f"❌ Authentication failed: {result}")
            return False

    except Exception as exc:
        print(f"❌ Connection error: {exc}")
        return False


def test_get_customers():
    """Test getting customer list."""
    print("\n📋 Testing get_customers...")

    session = requests.Session()

    # Authenticate first
    auth_resp = session.post(
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

    if not auth_resp.json().get("result", {}).get("uid"):
        print("❌ Authentication failed")
        return False

    # Get customers
    try:
        resp = session.post(
            f"{ODOO_URL}/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.partner",
                    "method": "search_read",
                    "args": [[["customer_rank", ">", 0]]],
                    "kwargs": {"fields": ["name", "email"], "limit": 5},
                },
            },
        )

        customers = resp.json().get("result", [])
        print(f"✅ Found {len(customers)} customers")

        for c in customers[:3]:
            print(f"   - {c.get('name', 'N/A')} ({c.get('email', 'no email')})")

        return True

    except Exception as exc:
        print(f"❌ Error: {exc}")
        return False


def test_financial_data():
    """Test getting financial data."""
    print("\n💰 Testing financial data access...")

    session = requests.Session()

    # Authenticate
    auth_resp = session.post(
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

    if not auth_resp.json().get("result", {}).get("uid"):
        print("❌ Authentication failed")
        return False

    # Get invoices
    try:
        resp = session.post(
            f"{ODOO_URL}/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "account.move",
                    "method": "search_count",
                    "args": [[["move_type", "=", "out_invoice"]]],
                    "kwargs": {},
                },
            },
        )

        count = resp.json().get("result", 0)
        print(f"✅ Found {count} invoices in system")
        return True

    except Exception as exc:
        print(f"❌ Error: {exc}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Odoo MCP Connection Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Authentication", test_authentication()))
    results.append(("Get Customers", test_get_customers()))
    results.append(("Financial Data", test_financial_data()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n🎉 All tests passed! Odoo MCP is ready to use.")
        print("\n📝 Available MCP Tools:")
        print("   1. get_financial_summary() - Revenue, expenses, profit")
        print("   2. create_invoice() - Create customer invoice")
        print("   3. get_customers() - List CRM customers")
        print("   4. create_expense() - Log business expense")
        print("   5. get_overdue_invoices() - Payment follow-ups")
    else:
        print("\n⚠️  Some tests failed. Check Odoo setup.")

    sys.exit(0 if all_passed else 1)
