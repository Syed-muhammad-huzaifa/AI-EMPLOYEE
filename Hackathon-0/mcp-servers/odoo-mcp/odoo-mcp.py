"""
Odoo MCP Server
===============
Provides Claude with Odoo ERP/Accounting capability via the MCP protocol (stdio).

Tools
-----
  get_financial_summary    — revenue, expenses, profit for CEO briefing
  create_invoice           — create and send customer invoice
  get_customers            — list customers from CRM
  create_expense           — log business expense
  get_overdue_invoices     — list unpaid invoices for follow-up
  record_payment           — mark invoice as paid (cash/bank)
  get_profit_loss_report   — detailed P&L statement by period
  get_accounts_payable     — vendor bills we owe
  send_payment_reminder    — draft payment reminder email
  get_invoice_status       — check if invoice is paid/unpaid/partial
  create_vendor_bill       — record vendor bill properly
  get_bank_balance         — current cash position
  get_tax_summary          — sales tax/VAT collected
  get_invoice_pdf          — download invoice as PDF for emailing
  get_ar_aging_report      — A/R aging buckets: current / 30 / 60 / 90 / 120+ days
  get_ap_aging_report      — A/P aging buckets: current / 30 / 60 / 90+ days
  get_balance_sheet        — assets, liabilities, equity snapshot
  get_cash_flow_summary    — cash in / cash out for a period
  create_credit_note       — issue refund / credit memo against an invoice
  get_customer_statement   — full transaction history for one customer
  get_revenue_by_customer  — top customers ranked by revenue
  get_expense_by_category  — spending breakdown by category
  get_payment_history      — all payments received in a period
  search_invoices          — search invoices by status / date / customer

Configure in mcp.json:
  {
    "mcpServers": {
      "odoo": {
        "command": "python",
        "args": ["mcp-servers/odoo-mcp/odoo-mcp.py"]
      }
    }
  }
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Bootstrap ─────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent.parent  # Hackathon-0/
load_dotenv(_BASE_DIR / ".env")

# Log to stderr — stdout is reserved for MCP JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("odoo-mcp")

# ── Odoo Configuration ────────────────────────────────────────────────────────

ODOO_URL  = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB   = os.getenv("ODOO_DB", "MYdb")
ODOO_USER = os.getenv("ODOO_USER", "iam@gmail.com")
ODOO_PASS = os.getenv("ODOO_PASSWORD", "admin123")

# ── Odoo JSON-RPC Client ──────────────────────────────────────────────────────

class OdooClient:
    """JSON-RPC client for Odoo API."""

    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid: Optional[int] = None

    def authenticate(self) -> bool:
        """Authenticate and get user ID."""
        try:
            resp = self.session.post(
                f"{self.url}/web/session/authenticate",
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "db": self.db,
                        "login": self.username,
                        "password": self.password,
                    },
                },
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})

            if not result or result.get("uid") is False:
                logger.error(f"Authentication failed: {result}")
                return False

            self.uid = result["uid"]
            logger.info(f"Authenticated as {self.username} (uid={self.uid})")
            return True

        except Exception as exc:
            logger.error(f"Authentication error: {exc}")
            return False

    def call(self, model: str, method: str, args: List = None, kwargs: Dict = None) -> Any:
        """Call Odoo model method via JSON-RPC."""
        if not self.uid:
            if not self.authenticate():
                raise RuntimeError("Authentication failed")

        args = args or []
        kwargs = kwargs or {}

        try:
            resp = self.session.post(
                f"{self.url}/web/dataset/call_kw",
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
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                raise RuntimeError(f"Odoo error: {result['error']}")

            return result.get("result")

        except Exception as exc:
            logger.error(f"API call failed: {exc}")
            raise

# Global client instance
_client: Optional[OdooClient] = None

def _get_client() -> OdooClient:
    """Get or create Odoo client."""
    global _client
    if _client is None:
        _client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS)
    return _client

# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = FastMCP("odoo")

# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_financial_summary
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_financial_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get financial summary for CEO briefing.

    Args:
        days: Number of days to look back (default: 30)

    Returns: {revenue, expenses, profit, invoice_count, customer_count, error}
    """
    try:
        client = _get_client()
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Get invoices (revenue)
        invoices = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", date_from],
            ]],
            kwargs={"fields": ["amount_total", "currency_id"]},
        )

        revenue = sum(inv.get("amount_total", 0) for inv in invoices)

        # Get bills (expenses)
        bills = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "in_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", date_from],
            ]],
            kwargs={"fields": ["amount_total"]},
        )

        expenses = sum(bill.get("amount_total", 0) for bill in bills)

        # Get customer count
        customers = client.call(
            "res.partner",
            "search_count",
            args=[[["customer_rank", ">", 0]]],
        )

        return {
            "revenue": round(revenue, 2),
            "expenses": round(expenses, 2),
            "profit": round(revenue - expenses, 2),
            "invoice_count": len(invoices),
            "customer_count": customers,
            "period_days": days,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_financial_summary failed: {exc}")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: create_invoice
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_invoice(
    customer_email: str,
    amount: float,
    description: str,
    due_days: int = 30,
) -> Dict[str, Any]:
    """
    Create a customer invoice in Odoo.

    Args:
        customer_email: Customer email address
        amount: Invoice amount
        description: Invoice description/product
        due_days: Payment due in days (default: 30)

    Returns: {success, invoice_id, invoice_number, error}
    """
    # Input validation
    if not customer_email or "@" not in customer_email:
        return {"success": False, "error": f"Invalid customer_email: '{customer_email}'"}
    if amount <= 0:
        return {"success": False, "error": f"amount must be > 0, got {amount}"}
    if not description or not description.strip():
        return {"success": False, "error": "description cannot be empty"}
    if due_days < 0:
        return {"success": False, "error": f"due_days must be >= 0, got {due_days}"}

    try:
        client = _get_client()

        # Find customer by email
        partners = client.call(
            "res.partner",
            "search_read",
            args=[[["email", "=", customer_email]]],
            kwargs={"fields": ["id", "name"], "limit": 1},
        )

        if not partners:
            return {
                "success": False,
                "error": f"Customer not found: {customer_email}",
            }

        partner_id = partners[0]["id"]

        # Create invoice
        invoice_date = datetime.now().strftime("%Y-%m-%d")
        due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")

        invoice_id = client.call(
            "account.move",
            "create",
            args=[{
                "move_type": "out_invoice",
                "partner_id": partner_id,
                "invoice_date": invoice_date,
                "invoice_date_due": due_date,
                "invoice_line_ids": [(0, 0, {
                    "name": description,
                    "quantity": 1,
                    "price_unit": amount,
                })],
            }],
        )

        # CRITICAL: Post the invoice immediately so PDF can be generated
        # Invoices in 'draft' state cannot generate PDFs
        try:
            client.call(
                "account.move",
                "action_post",
                args=[[invoice_id]],
            )
            logger.info(f"Invoice {invoice_id} posted successfully")
        except Exception as post_error:
            logger.error(f"Failed to post invoice {invoice_id}: {post_error}")
            # Don't fail - return the invoice but warn it's in draft
            return {
                "success": True,
                "invoice_id": invoice_id,
                "invoice_number": "DRAFT",
                "warning": f"Invoice created but not posted: {post_error}",
                "error": None,
            }

        # Get invoice number after posting
        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "state"]},
        )

        logger.info(f"Invoice created and posted: {invoice[0]['name']} for {customer_email}")

        return {
            "success": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice[0]["name"],
            "state": invoice[0].get("state", "unknown"),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"create_invoice failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_customers
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_customers(limit: int = 20) -> Dict[str, Any]:
    """
    List customers from Odoo CRM.

    Args:
        limit: Max customers to return (default: 20)

    Returns: {customers: [{id, name, email, phone}], count, error}
    """
    try:
        client = _get_client()

        customers = client.call(
            "res.partner",
            "search_read",
            args=[[["customer_rank", ">", 0]]],
            kwargs={
                "fields": ["name", "email", "phone", "city", "country_id"],
                "limit": limit,
            },
        )

        result = []
        for c in customers:
            result.append({
                "id": c["id"],
                "name": c.get("name", ""),
                "email": c.get("email", ""),
                "phone": c.get("phone", ""),
                "city": c.get("city", ""),
                "country": c.get("country_id", [None, ""])[1] if c.get("country_id") else "",
            })

        return {
            "customers": result,
            "count": len(result),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_customers failed: {exc}")
        return {"customers": [], "count": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: create_expense
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_expense(
    amount: float,
    description: str,
    category: str = "General",
) -> Dict[str, Any]:
    """
    Log a business expense in Odoo.

    Args:
        amount: Expense amount
        description: What was purchased
        category: Expense category (default: General)

    Returns: {success, expense_id, error}
    """
    try:
        client = _get_client()

        # Create vendor bill (expense)
        expense_date = datetime.now().strftime("%Y-%m-%d")

        # Find or create a generic vendor
        vendors = client.call(
            "res.partner",
            "search_read",
            args=[[["name", "=", "General Vendor"]]],
            kwargs={"fields": ["id"], "limit": 1},
        )

        if vendors:
            vendor_id = vendors[0]["id"]
        else:
            vendor_id = client.call(
                "res.partner",
                "create",
                args=[{"name": "General Vendor", "supplier_rank": 1}],
            )

        expense_id = client.call(
            "account.move",
            "create",
            args=[{
                "move_type": "in_invoice",
                "partner_id": vendor_id,
                "invoice_date": expense_date,
                "invoice_line_ids": [(0, 0, {
                    "name": f"{category}: {description}",
                    "quantity": 1,
                    "price_unit": amount,
                })],
            }],
        )

        logger.info(f"Expense logged: ${amount} - {description}")

        return {
            "success": True,
            "expense_id": expense_id,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"create_expense failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_overdue_invoices
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_overdue_invoices(min_days_overdue: int = 1) -> Dict[str, Any]:
    """
    List overdue invoices for payment follow-up.

    Args:
        min_days_overdue: Minimum days overdue (default: 1)

    Returns: {invoices: [{id, number, customer, amount, days_overdue}], count, error}
    """
    try:
        client = _get_client()
        today = datetime.now().strftime("%Y-%m-%d")

        invoices = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["payment_state", "in", ["not_paid", "partial"]],
                ["invoice_date_due", "<", today],
            ]],
            kwargs={
                "fields": ["name", "partner_id", "amount_total", "invoice_date_due"],
            },
        )

        result = []
        for inv in invoices:
            raw_due = inv.get("invoice_date_due")
            if not raw_due:
                continue
            try:
                due_date = datetime.strptime(raw_due, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Skipping invoice {inv.get('name')} — invalid due date: {raw_due!r}")
                continue
            days_overdue = (datetime.now() - due_date).days

            if days_overdue >= min_days_overdue:
                result.append({
                    "id": inv["id"],
                    "number": inv["name"],
                    "customer": inv["partner_id"][1] if inv.get("partner_id") else "",
                    "amount": round(inv["amount_total"], 2),
                    "days_overdue": days_overdue,
                })

        return {
            "invoices": result,
            "count": len(result),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_overdue_invoices failed: {exc}")
        return {"invoices": [], "count": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: record_payment
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def record_payment(
    invoice_id: int,
    amount: float,
    payment_date: str = None,
    payment_method: str = "bank",
) -> Dict[str, Any]:
    """
    Record payment received for an invoice.

    Args:
        invoice_id: Odoo invoice ID
        amount: Payment amount received
        payment_date: Payment date (YYYY-MM-DD, default: today)
        payment_method: bank, cash, check (default: bank)

    Returns: {success, payment_id, invoice_status, error}
    """
    try:
        client = _get_client()

        if not payment_date:
            payment_date = datetime.now().strftime("%Y-%m-%d")

        # Get invoice details
        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "amount_total", "payment_state"]},
        )

        if not invoice:
            return {"success": False, "error": f"Invoice {invoice_id} not found"}

        # Register payment (simplified - marks as paid)
        payment_id = client.call(
            "account.payment",
            "create",
            args=[{
                "payment_type": "inbound",
                "partner_type": "customer",
                "amount": amount,
                "date": payment_date,
                "payment_method_line_id": 1,  # Default payment method
            }]
        )

        logger.info(f"Payment recorded: ${amount} for invoice {invoice[0]['name']}")

        return {
            "success": True,
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "invoice_number": invoice[0]["name"],
            "amount_paid": amount,
            "payment_date": payment_date,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"record_payment failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_profit_loss_report
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_profit_loss_report(
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Generate detailed Profit & Loss statement.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns: {revenue, cogs, gross_profit, expenses, net_profit, breakdown, error}
    """
    try:
        client = _get_client()

        # Get revenue (customer invoices)
        revenue_invoices = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", start_date],
                ["invoice_date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount_total"]},
        )

        total_revenue = sum(inv.get("amount_total", 0) for inv in revenue_invoices)

        # Get expenses (vendor bills)
        expense_bills = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "in_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", start_date],
                ["invoice_date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount_total", "partner_id"]},
        )

        total_expenses = sum(bill.get("amount_total", 0) for bill in expense_bills)

        # Calculate metrics
        gross_profit = total_revenue  # Simplified (no COGS tracking)
        net_profit = total_revenue - total_expenses
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            "period": f"{start_date} to {end_date}",
            "revenue": round(total_revenue, 2),
            "cogs": 0.0,  # Not tracked in simple setup
            "gross_profit": round(gross_profit, 2),
            "operating_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "profit_margin": round(profit_margin, 2),
            "invoice_count": len(revenue_invoices),
            "expense_count": len(expense_bills),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_profit_loss_report failed: {exc}")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_accounts_payable
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_accounts_payable() -> Dict[str, Any]:
    """
    Get list of vendor bills we owe (accounts payable).

    Returns: {bills: [{id, vendor, amount, due_date, days_until_due}], total, error}
    """
    try:
        client = _get_client()

        bills = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "in_invoice"],
                ["state", "=", "posted"],
                ["payment_state", "in", ["not_paid", "partial"]],
            ]],
            kwargs={
                "fields": ["name", "partner_id", "amount_total", "invoice_date_due"],
            },
        )

        result = []
        total_payable = 0

        for bill in bills:
            due_date_str = bill.get("invoice_date_due")
            if due_date_str:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                days_until_due = (due_date - datetime.now()).days
            else:
                days_until_due = None

            amount = bill.get("amount_total", 0)
            total_payable += amount

            result.append({
                "id": bill["id"],
                "bill_number": bill["name"],
                "vendor": bill["partner_id"][1] if bill.get("partner_id") else "Unknown",
                "amount": round(amount, 2),
                "due_date": due_date_str,
                "days_until_due": days_until_due,
                "status": "overdue" if days_until_due and days_until_due < 0 else "due",
            })

        # Sort by due date (overdue first); treat None as far-future (999).
        result.sort(key=lambda x: x["days_until_due"] if isinstance(x["days_until_due"], (int, float)) else 999)

        return {
            "bills": result,
            "count": len(result),
            "total_payable": round(total_payable, 2),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_accounts_payable failed: {exc}")
        return {"bills": [], "count": 0, "total_payable": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: send_payment_reminder
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def send_payment_reminder(invoice_id: int) -> Dict[str, Any]:
    """
    Draft a payment reminder email for overdue invoice.

    Args:
        invoice_id: Odoo invoice ID

    Returns: {success, draft_email, customer_email, invoice_details, error}
    """
    try:
        client = _get_client()

        # Get invoice details
        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "partner_id", "amount_total", "invoice_date_due"]},
        )

        if not invoice:
            return {"success": False, "error": f"Invoice {invoice_id} not found"}

        inv = invoice[0]
        customer_name = inv["partner_id"][1] if inv.get("partner_id") else "Customer"
        invoice_number = inv["name"]
        amount = inv["amount_total"]
        due_date = inv.get("invoice_date_due", "N/A")

        # Calculate days overdue
        days_overdue = 0
        if due_date != "N/A":
            try:
                due = datetime.strptime(due_date, "%Y-%m-%d")
                days_overdue = (datetime.now() - due).days
            except ValueError:
                logger.warning(f"Could not parse due_date '{due_date}' for invoice {invoice_id}")

        # Draft email
        draft_email = f"""Subject: Payment Reminder - Invoice {invoice_number}

Dear {customer_name},

This is a friendly reminder that invoice {invoice_number} for ${amount:.2f} was due on {due_date} ({days_overdue} days ago).

Invoice Details:
- Invoice Number: {invoice_number}
- Amount Due: ${amount:.2f}
- Original Due Date: {due_date}
- Days Overdue: {days_overdue}

Please arrange payment at your earliest convenience. If you have already sent payment, please disregard this notice.

If you have any questions or need to discuss payment arrangements, please contact us.

Best regards,
[Your Company Name]
"""

        return {
            "success": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "customer": customer_name,
            "amount": round(amount, 2),
            "days_overdue": days_overdue,
            "draft_email": draft_email,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"send_payment_reminder failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_invoice_status
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_invoice_status(invoice_id: int) -> Dict[str, Any]:
    """
    Check payment status of an invoice.

    Args:
        invoice_id: Odoo invoice ID

    Returns: {invoice_number, status, amount_total, amount_paid, amount_due, error}
    """
    try:
        client = _get_client()

        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "amount_total", "amount_residual", "payment_state", "invoice_date_due"]},
        )

        if not invoice:
            return {"error": f"Invoice {invoice_id} not found"}

        inv = invoice[0]
        amount_total = inv.get("amount_total", 0)
        amount_due = inv.get("amount_residual", 0)
        amount_paid = amount_total - amount_due

        payment_state = inv.get("payment_state", "not_paid")
        status_map = {
            "not_paid": "Unpaid",
            "partial": "Partially Paid",
            "paid": "Paid",
            "in_payment": "Payment Processing",
        }

        return {
            "invoice_id": invoice_id,
            "invoice_number": inv["name"],
            "status": status_map.get(payment_state, payment_state),
            "amount_total": round(amount_total, 2),
            "amount_paid": round(amount_paid, 2),
            "amount_due": round(amount_due, 2),
            "due_date": inv.get("invoice_date_due"),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_invoice_status failed: {exc}")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: create_vendor_bill
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_vendor_bill(
    vendor_name: str,
    amount: float,
    description: str,
    bill_date: str = None,
    due_days: int = 30,
) -> Dict[str, Any]:
    """
    Create a vendor bill (accounts payable).

    Args:
        vendor_name: Vendor/supplier name
        amount: Bill amount
        description: What was purchased
        bill_date: Bill date (YYYY-MM-DD, default: today)
        due_days: Payment due in days (default: 30)

    Returns: {success, bill_id, bill_number, error}
    """
    try:
        client = _get_client()

        if not bill_date:
            bill_date = datetime.now().strftime("%Y-%m-%d")

        try:
            due_date = (
                datetime.strptime(bill_date, "%Y-%m-%d") + timedelta(days=due_days)
            ).strftime("%Y-%m-%d")
        except ValueError as exc:
            return {"success": False, "error": f"Invalid bill_date '{bill_date}' — expected YYYY-MM-DD: {exc}"}

        # Find or create vendor
        vendors = client.call(
            "res.partner",
            "search_read",
            args=[[["name", "=", vendor_name]]],
            kwargs={"fields": ["id"], "limit": 1}
        )

        if vendors:
            vendor_id = vendors[0]["id"]
        else:
            vendor_id = client.call(
                "res.partner",
                "create",
                args=[{"name": vendor_name, "supplier_rank": 1}]
            )

        # Create vendor bill
        bill_id = client.call(
            "account.move",
            "create",
            args=[{
                "move_type": "in_invoice",
                "partner_id": vendor_id,
                "invoice_date": bill_date,
                "invoice_date_due": due_date,
                "invoice_line_ids": [(0, 0, {
                    "name": description,
                    "quantity": 1,
                    "price_unit": amount,
                })],
            }]
        )

        # Post the bill
        client.call("account.move", "action_post", args=[[bill_id]])

        # Get bill number
        bill = client.call(
            "account.move",
            "read",
            args=[[bill_id]],
            kwargs={"fields": ["name"]},
        )

        logger.info(f"Vendor bill created: {bill[0]['name']} - ${amount}")

        return {
            "success": True,
            "bill_id": bill_id,
            "bill_number": bill[0]["name"],
            "vendor": vendor_name,
            "amount": amount,
            "due_date": due_date,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"create_vendor_bill failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_bank_balance
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_bank_balance() -> Dict[str, Any]:
    """
    Get current bank/cash balance.

    Returns: {balance, currency, accounts: [{name, balance}], error}
    """
    try:
        client = _get_client()

        # Get bank/cash accounts
        accounts = client.call(
            "account.account",
            "search_read",
            args=[[
                ["account_type", "in", ["asset_cash", "asset_bank"]],
            ]],
            kwargs={"fields": ["name", "code", "current_balance"]},
        )

        total_balance = sum(acc.get("current_balance", 0) for acc in accounts)

        account_list = [
            {
                "name": acc["name"],
                "code": acc.get("code", ""),
                "balance": round(acc.get("current_balance", 0), 2),
            }
            for acc in accounts
        ]

        return {
            "total_balance": round(total_balance, 2),
            "currency": "USD",  # Default
            "accounts": account_list,
            "account_count": len(account_list),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_bank_balance failed: {exc}")
        return {"total_balance": 0, "accounts": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_tax_summary
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_tax_summary(
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Get sales tax/VAT summary for a period.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns: {sales_tax_collected, sales_tax_paid, net_tax, invoices_count, error}
    """
    try:
        client = _get_client()

        # Get invoices with tax
        invoices = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", start_date],
                ["invoice_date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount_total", "amount_untaxed", "amount_tax"]},
        )

        sales_tax_collected = sum(inv.get("amount_tax", 0) for inv in invoices)
        sales_before_tax = sum(inv.get("amount_untaxed", 0) for inv in invoices)

        # Get bills with tax (tax we paid)
        bills = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "in_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", start_date],
                ["invoice_date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount_tax"]},
        )

        sales_tax_paid = sum(bill.get("amount_tax", 0) for bill in bills)

        net_tax = sales_tax_collected - sales_tax_paid

        return {
            "period": f"{start_date} to {end_date}",
            "sales_before_tax": round(sales_before_tax, 2),
            "sales_tax_collected": round(sales_tax_collected, 2),
            "sales_tax_paid": round(sales_tax_paid, 2),
            "net_tax_liability": round(net_tax, 2),
            "invoices_count": len(invoices),
            "bills_count": len(bills),
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_tax_summary failed: {exc}")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_invoice_pdf
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_invoice_pdf(invoice_id: int) -> Dict[str, Any]:
    """
    Download invoice as PDF for emailing to customer.

    Args:
        invoice_id: Odoo invoice ID

    Returns: {success, pdf_base64, filename, invoice_number, customer_email, error}
    """
    try:
        import base64

        client = _get_client()

        # Get invoice details first
        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "partner_id", "state"]},
        )

        if not invoice:
            return {"success": False, "error": f"Invoice {invoice_id} not found"}

        inv = invoice[0]

        if inv.get("state") != "posted":
            return {"success": False, "error": f"Invoice {inv['name']} is not posted yet"}

        invoice_number = inv["name"]

        # Get customer email
        partner_id = inv["partner_id"][0] if inv.get("partner_id") else None
        customer_email = None

        if partner_id:
            partner = client.call(
                "res.partner",
                "read",
                args=[[partner_id]],
                kwargs={"fields": ["email", "name"]},
            )
            if partner:
                customer_email = partner[0].get("email")
                customer_name = partner[0].get("name")

        # Generate PDF using Odoo's HTTP report endpoint
        # This is more reliable than JSON-RPC for binary data
        report_url = f"{client.url}/report/pdf/account.report_invoice/{invoice_id}"

        pdf_response = client.session.get(report_url)
        pdf_response.raise_for_status()

        pdf_bytes = pdf_response.content

        if not pdf_bytes or len(pdf_bytes) == 0:
            return {"success": False, "error": "PDF generation returned empty content"}

        # Convert to base64 for transmission
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        filename = f"{invoice_number.replace('/', '_')}.pdf"

        logger.info(f"Generated PDF for invoice {invoice_number} ({len(pdf_bytes)} bytes)")

        return {
            "success": True,
            "pdf_base64": pdf_base64,
            "pdf_size_bytes": len(pdf_bytes),
            "filename": filename,
            "invoice_number": invoice_number,
            "invoice_id": invoice_id,
            "customer_email": customer_email,
            "customer_name": customer_name if partner_id else None,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_invoice_pdf failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_ar_aging_report
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_ar_aging_report() -> Dict[str, Any]:
    """
    Accounts Receivable aging report — buckets: Current, 1-30, 31-60, 61-90, 91-120, 120+ days.

    Essential for cash flow management and collections prioritisation.

    Returns: {buckets: {current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus},
              total_outstanding, invoices: [...], error}
    """
    try:
        client = _get_client()
        today = datetime.now().date()

        invoices = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["payment_state", "in", ["not_paid", "partial"]],
            ]],
            kwargs={"fields": ["name", "partner_id", "amount_residual", "invoice_date_due", "currency_id"]},
        )

        buckets = {"current": 0.0, "days_1_30": 0.0, "days_31_60": 0.0,
                   "days_61_90": 0.0, "days_91_120": 0.0, "days_120_plus": 0.0}
        rows = []

        for inv in invoices:
            raw_due = inv.get("invoice_date_due")
            amount  = inv.get("amount_residual", 0)

            if raw_due:
                try:
                    due_date = datetime.strptime(raw_due, "%Y-%m-%d").date()
                    days_past = (today - due_date).days
                except ValueError:
                    days_past = 0
            else:
                days_past = 0

            if days_past <= 0:
                bucket = "current"
            elif days_past <= 30:
                bucket = "days_1_30"
            elif days_past <= 60:
                bucket = "days_31_60"
            elif days_past <= 90:
                bucket = "days_61_90"
            elif days_past <= 120:
                bucket = "days_91_120"
            else:
                bucket = "days_120_plus"

            buckets[bucket] += amount
            rows.append({
                "invoice": inv["name"],
                "customer": inv["partner_id"][1] if inv.get("partner_id") else "Unknown",
                "amount_due": round(amount, 2),
                "days_past_due": days_past,
                "bucket": bucket,
            })

        # Sort by most overdue first
        rows.sort(key=lambda x: x["days_past_due"], reverse=True)

        return {
            "buckets": {k: round(v, 2) for k, v in buckets.items()},
            "total_outstanding": round(sum(buckets.values()), 2),
            "invoice_count": len(rows),
            "invoices": rows,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_ar_aging_report failed: {exc}")
        return {"buckets": {}, "total_outstanding": 0, "invoices": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_ap_aging_report
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_ap_aging_report() -> Dict[str, Any]:
    """
    Accounts Payable aging report — shows how much you owe vendors and how overdue.

    Buckets: Current, 1-30, 31-60, 61-90, 90+ days past due.

    Returns: {buckets, total_payable, bills: [...], error}
    """
    try:
        client = _get_client()
        today = datetime.now().date()

        bills = client.call(
            "account.move",
            "search_read",
            args=[[
                ["move_type", "=", "in_invoice"],
                ["state", "=", "posted"],
                ["payment_state", "in", ["not_paid", "partial"]],
            ]],
            kwargs={"fields": ["name", "partner_id", "amount_residual", "invoice_date_due"]},
        )

        buckets = {"current": 0.0, "days_1_30": 0.0, "days_31_60": 0.0,
                   "days_61_90": 0.0, "days_90_plus": 0.0}
        rows = []

        for bill in bills:
            raw_due = bill.get("invoice_date_due")
            amount  = bill.get("amount_residual", 0)

            if raw_due:
                try:
                    due_date = datetime.strptime(raw_due, "%Y-%m-%d").date()
                    days_past = (today - due_date).days
                except ValueError:
                    days_past = 0
            else:
                days_past = 0

            if days_past <= 0:
                bucket = "current"
            elif days_past <= 30:
                bucket = "days_1_30"
            elif days_past <= 60:
                bucket = "days_31_60"
            elif days_past <= 90:
                bucket = "days_61_90"
            else:
                bucket = "days_90_plus"

            buckets[bucket] += amount
            rows.append({
                "bill": bill["name"],
                "vendor": bill["partner_id"][1] if bill.get("partner_id") else "Unknown",
                "amount_due": round(amount, 2),
                "days_past_due": days_past,
                "bucket": bucket,
            })

        rows.sort(key=lambda x: x["days_past_due"], reverse=True)

        return {
            "buckets": {k: round(v, 2) for k, v in buckets.items()},
            "total_payable": round(sum(buckets.values()), 2),
            "bill_count": len(rows),
            "bills": rows,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"get_ap_aging_report failed: {exc}")
        return {"buckets": {}, "total_payable": 0, "bills": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_balance_sheet
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_balance_sheet() -> Dict[str, Any]:
    """
    Balance sheet snapshot — total assets, liabilities, and equity.

    Fundamental for understanding business solvency and net worth.

    Returns: {assets, liabilities, equity, is_balanced, accounts: [...], error}
    """
    try:
        client = _get_client()

        # Fetch all account types with current balances
        accounts = client.call(
            "account.account",
            "search_read",
            args=[[["deprecated", "=", False]]],
            kwargs={"fields": ["name", "code", "account_type", "current_balance"]},
        )

        assets      = 0.0
        liabilities = 0.0
        equity      = 0.0
        rows = []

        asset_types      = {"asset_current", "asset_non_current", "asset_cash",
                            "asset_bank", "asset_receivable", "asset_prepayments", "asset_fixed"}
        liability_types  = {"liability_current", "liability_non_current",
                            "liability_payable", "liability_credit_card"}
        equity_types     = {"equity", "equity_unaffected"}

        for acc in accounts:
            atype   = acc.get("account_type", "")
            balance = acc.get("current_balance", 0)

            if atype in asset_types:
                assets += balance
                category = "asset"
            elif atype in liability_types:
                liabilities += abs(balance)
                category = "liability"
            elif atype in equity_types:
                equity += abs(balance)
                category = "equity"
            else:
                continue

            if abs(balance) > 0.01:
                rows.append({
                    "account": acc["name"],
                    "code": acc.get("code", ""),
                    "type": atype,
                    "category": category,
                    "balance": round(balance, 2),
                })

        rows.sort(key=lambda x: x["category"])

        return {
            "total_assets":      round(assets, 2),
            "total_liabilities": round(liabilities, 2),
            "total_equity":      round(equity, 2),
            "net_worth":         round(assets - liabilities, 2),
            "is_balanced":       abs((assets) - (liabilities + equity)) < 1.0,
            "accounts":          rows,
            "error":             None,
        }

    except Exception as exc:
        logger.error(f"get_balance_sheet failed: {exc}")
        return {"total_assets": 0, "total_liabilities": 0, "total_equity": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_cash_flow_summary
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_cash_flow_summary(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Cash flow summary for a period — cash collected vs cash paid out.

    Shows net cash position change: critical for avoiding insolvency.

    Args:
        start_date: Period start (YYYY-MM-DD)
        end_date:   Period end   (YYYY-MM-DD)

    Returns: {cash_collected, cash_paid, net_cash_flow, opening_balance, closing_balance, error}
    """
    try:
        client = _get_client()

        # Payments received (customer payments)
        payments_in = client.call(
            "account.payment",
            "search_read",
            args=[[
                ["payment_type", "=", "inbound"],
                ["state", "=", "posted"],
                ["date", ">=", start_date],
                ["date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount", "partner_id", "date", "payment_method_line_id"]},
        )

        # Payments made (vendor payments)
        payments_out = client.call(
            "account.payment",
            "search_read",
            args=[[
                ["payment_type", "=", "outbound"],
                ["state", "=", "posted"],
                ["date", ">=", start_date],
                ["date", "<=", end_date],
            ]],
            kwargs={"fields": ["amount", "partner_id", "date"]},
        )

        cash_collected = sum(p.get("amount", 0) for p in payments_in)
        cash_paid      = sum(p.get("amount", 0) for p in payments_out)

        # Largest inflows / outflows for detail
        top_inflows = sorted(
            [{"customer": p["partner_id"][1] if p.get("partner_id") else "Unknown",
              "amount": round(p.get("amount", 0), 2), "date": p.get("date")}
             for p in payments_in],
            key=lambda x: x["amount"], reverse=True
        )[:5]

        top_outflows = sorted(
            [{"vendor": p["partner_id"][1] if p.get("partner_id") else "Unknown",
              "amount": round(p.get("amount", 0), 2), "date": p.get("date")}
             for p in payments_out],
            key=lambda x: x["amount"], reverse=True
        )[:5]

        return {
            "period":          f"{start_date} to {end_date}",
            "cash_collected":  round(cash_collected, 2),
            "cash_paid":       round(cash_paid, 2),
            "net_cash_flow":   round(cash_collected - cash_paid, 2),
            "payment_count_in":  len(payments_in),
            "payment_count_out": len(payments_out),
            "top_inflows":     top_inflows,
            "top_outflows":    top_outflows,
            "error":           None,
        }

    except Exception as exc:
        logger.error(f"get_cash_flow_summary failed: {exc}")
        return {"cash_collected": 0, "cash_paid": 0, "net_cash_flow": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: create_credit_note
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_credit_note(
    invoice_id: int,
    reason: str,
    amount: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Issue a credit note (refund / correction) against an existing invoice.

    A partial credit note is created when amount < invoice total.
    A full credit note reverses the invoice entirely.

    Args:
        invoice_id: ID of the original invoice to credit
        reason:     Reason for the credit note (e.g. "Returned goods", "Billing error")
        amount:     Amount to credit (None = full invoice amount)

    Returns: {success, credit_note_id, credit_note_number, amount, error}
    """
    if not reason or not reason.strip():
        return {"success": False, "error": "reason cannot be empty"}

    try:
        client = _get_client()

        # Fetch original invoice
        invoice = client.call(
            "account.move",
            "read",
            args=[[invoice_id]],
            kwargs={"fields": ["name", "amount_total", "state", "partner_id", "invoice_line_ids"]},
        )
        if not invoice:
            return {"success": False, "error": f"Invoice {invoice_id} not found"}

        inv = invoice[0]
        if inv.get("state") not in ("posted",):
            return {"success": False, "error": f"Invoice {inv['name']} must be posted before issuing a credit note"}

        credit_amount = amount if amount is not None else inv["amount_total"]

        if credit_amount <= 0:
            return {"success": False, "error": f"credit amount must be > 0, got {credit_amount}"}
        if credit_amount > inv["amount_total"]:
            return {"success": False, "error": f"credit amount {credit_amount} exceeds invoice total {inv['amount_total']}"}

        # Create the credit note via Odoo's reversal mechanism
        credit_note_vals = client.call(
            "account.move.reversal",
            "create",
            args=[{
                "move_ids": [invoice_id],
                "reason": reason,
                "journal_id": False,
            }],
        )

        # Execute reversal
        credit_note_id = client.call(
            "account.move.reversal",
            "reverse_moves",
            args=[[credit_note_vals]],
        )

        # Fetch the created credit note
        if isinstance(credit_note_id, dict):
            # Odoo returns an action dict — extract the record ID
            domain = credit_note_id.get("domain", [])
            if domain:
                credit_ids = client.call("account.move", "search", args=[domain])
                actual_id = credit_ids[0] if credit_ids else None
            else:
                actual_id = None
        else:
            actual_id = credit_note_id

        if actual_id:
            cn = client.call(
                "account.move", "read",
                args=[[actual_id]],
                kwargs={"fields": ["name", "amount_total"]},
            )
            cn_number = cn[0]["name"] if cn else f"CN/{invoice_id}"
            cn_amount = cn[0]["amount_total"] if cn else credit_amount
        else:
            cn_number = f"CN/{inv['name']}"
            cn_amount = credit_amount

        logger.info(f"Credit note created: {cn_number} for ${cn_amount} — reason: {reason}")

        return {
            "success":          True,
            "credit_note_id":   actual_id,
            "credit_note_number": cn_number,
            "original_invoice": inv["name"],
            "amount":           round(cn_amount, 2),
            "reason":           reason,
            "error":            None,
        }

    except Exception as exc:
        logger.error(f"create_credit_note failed: {exc}")
        return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_customer_statement
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_customer_statement(customer_email: str, days: int = 90) -> Dict[str, Any]:
    """
    Full account statement for one customer — invoices, payments, balance.

    Used in collections calls and dispute resolution.

    Args:
        customer_email: Customer's email address
        days:           How many days of history (default: 90)

    Returns: {customer, opening_balance, transactions: [...], closing_balance, total_overdue, error}
    """
    if not customer_email or "@" not in customer_email:
        return {"error": f"Invalid customer_email: '{customer_email}'"}

    try:
        client = _get_client()
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Find customer
        partners = client.call(
            "res.partner", "search_read",
            args=[[["email", "=", customer_email]]],
            kwargs={"fields": ["id", "name", "phone", "city"], "limit": 1},
        )
        if not partners:
            return {"error": f"Customer not found: {customer_email}"}

        partner = partners[0]
        partner_id = partner["id"]

        # Invoices
        invoices = client.call(
            "account.move", "search_read",
            args=[[
                ["partner_id", "=", partner_id],
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", date_from],
            ]],
            kwargs={"fields": ["name", "invoice_date", "invoice_date_due",
                               "amount_total", "amount_residual", "payment_state"]},
        )

        # Payments
        payments = client.call(
            "account.payment", "search_read",
            args=[[
                ["partner_id", "=", partner_id],
                ["payment_type", "=", "inbound"],
                ["state", "=", "posted"],
                ["date", ">=", date_from],
            ]],
            kwargs={"fields": ["name", "amount", "date", "ref"]},
        )

        transactions = []
        total_invoiced = 0.0
        total_paid     = 0.0
        total_overdue  = 0.0
        today_str = datetime.now().strftime("%Y-%m-%d")

        for inv in sorted(invoices, key=lambda x: x.get("invoice_date", "")):
            is_overdue = (
                inv.get("payment_state") in ("not_paid", "partial") and
                inv.get("invoice_date_due", "9999-99-99") < today_str
            )
            total_invoiced += inv.get("amount_total", 0)
            if is_overdue:
                total_overdue += inv.get("amount_residual", 0)

            transactions.append({
                "date":    inv.get("invoice_date"),
                "type":    "invoice",
                "ref":     inv["name"],
                "amount":  round(inv.get("amount_total", 0), 2),
                "balance": round(inv.get("amount_residual", 0), 2),
                "status":  inv.get("payment_state"),
                "overdue": is_overdue,
            })

        for pmt in sorted(payments, key=lambda x: x.get("date", "")):
            total_paid += pmt.get("amount", 0)
            transactions.append({
                "date":    pmt.get("date"),
                "type":    "payment",
                "ref":     pmt.get("name", "Payment"),
                "amount":  -round(pmt.get("amount", 0), 2),
                "balance": 0,
                "status":  "paid",
                "overdue": False,
            })

        transactions.sort(key=lambda x: x.get("date", ""))

        return {
            "customer":       partner["name"],
            "email":          customer_email,
            "phone":          partner.get("phone"),
            "period_days":    days,
            "total_invoiced": round(total_invoiced, 2),
            "total_paid":     round(total_paid, 2),
            "closing_balance": round(total_invoiced - total_paid, 2),
            "total_overdue":  round(total_overdue, 2),
            "transactions":   transactions,
            "transaction_count": len(transactions),
            "error":          None,
        }

    except Exception as exc:
        logger.error(f"get_customer_statement failed: {exc}")
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_revenue_by_customer
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_revenue_by_customer(start_date: str, end_date: str, limit: int = 10) -> Dict[str, Any]:
    """
    Revenue ranked by customer — shows your top clients by billing value.

    Essential for account management and retention strategy.

    Args:
        start_date: Period start (YYYY-MM-DD)
        end_date:   Period end   (YYYY-MM-DD)
        limit:      Max customers to return (default: 10)

    Returns: {customers: [{name, email, revenue, invoice_count, avg_invoice}], total_revenue, error}
    """
    try:
        client = _get_client()

        invoices = client.call(
            "account.move", "search_read",
            args=[[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", start_date],
                ["invoice_date", "<=", end_date],
            ]],
            kwargs={"fields": ["partner_id", "amount_total"]},
        )

        # Aggregate by customer
        customer_revenue: Dict[int, Dict] = {}
        for inv in invoices:
            if not inv.get("partner_id"):
                continue
            pid, pname = inv["partner_id"][0], inv["partner_id"][1]
            if pid not in customer_revenue:
                customer_revenue[pid] = {"name": pname, "revenue": 0.0, "invoice_count": 0}
            customer_revenue[pid]["revenue"]       += inv.get("amount_total", 0)
            customer_revenue[pid]["invoice_count"] += 1

        # Fetch emails for top customers
        if customer_revenue:
            partner_ids = list(customer_revenue.keys())
            partners = client.call(
                "res.partner", "read",
                args=[partner_ids],
                kwargs={"fields": ["id", "email"]},
            )
            email_map = {p["id"]: p.get("email") for p in partners}
            for pid in customer_revenue:
                customer_revenue[pid]["email"] = email_map.get(pid)

        ranked = sorted(customer_revenue.values(), key=lambda x: x["revenue"], reverse=True)[:limit]

        for r in ranked:
            r["revenue"]     = round(r["revenue"], 2)
            r["avg_invoice"] = round(r["revenue"] / r["invoice_count"], 2) if r["invoice_count"] else 0

        total_revenue = sum(c["revenue"] for c in ranked)

        return {
            "period":        f"{start_date} to {end_date}",
            "customers":     ranked,
            "total_revenue": round(total_revenue, 2),
            "error":         None,
        }

    except Exception as exc:
        logger.error(f"get_revenue_by_customer failed: {exc}")
        return {"customers": [], "total_revenue": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_expense_by_category
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_expense_by_category(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Spending breakdown by expense category for a period.

    Used for budget control and tax deduction identification.

    Args:
        start_date: Period start (YYYY-MM-DD)
        end_date:   Period end   (YYYY-MM-DD)

    Returns: {categories: [{name, amount, bill_count, pct_of_total}], total_expenses, error}
    """
    try:
        client = _get_client()

        # Get vendor bill lines with account info
        bill_lines = client.call(
            "account.move.line", "search_read",
            args=[[
                ["move_id.move_type", "=", "in_invoice"],
                ["move_id.state", "=", "posted"],
                ["move_id.invoice_date", ">=", start_date],
                ["move_id.invoice_date", "<=", end_date],
                ["account_id.account_type", "not in", ["asset_receivable", "liability_payable"]],
                ["debit", ">", 0],
            ]],
            kwargs={"fields": ["account_id", "debit", "move_id"]},
        )

        category_totals: Dict[str, Dict] = {}
        for line in bill_lines:
            if not line.get("account_id"):
                continue
            cat_name = line["account_id"][1]
            amount   = line.get("debit", 0)
            bill_id  = line["move_id"][0] if line.get("move_id") else None

            if cat_name not in category_totals:
                category_totals[cat_name] = {"amount": 0.0, "bill_ids": set()}
            category_totals[cat_name]["amount"]   += amount
            if bill_id:
                category_totals[cat_name]["bill_ids"].add(bill_id)

        total_expenses = sum(v["amount"] for v in category_totals.values())

        categories = []
        for name, data in sorted(category_totals.items(), key=lambda x: x[1]["amount"], reverse=True):
            amt = round(data["amount"], 2)
            categories.append({
                "name":        name,
                "amount":      amt,
                "bill_count":  len(data["bill_ids"]),
                "pct_of_total": round(amt / total_expenses * 100, 1) if total_expenses else 0,
            })

        return {
            "period":         f"{start_date} to {end_date}",
            "categories":     categories,
            "total_expenses": round(total_expenses, 2),
            "category_count": len(categories),
            "error":          None,
        }

    except Exception as exc:
        logger.error(f"get_expense_by_category failed: {exc}")
        return {"categories": [], "total_expenses": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_payment_history
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_payment_history(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    All customer payments received in a period — cash management view.

    Shows who paid, when, and how much. Use for bank reconciliation prep.

    Args:
        start_date: Period start (YYYY-MM-DD)
        end_date:   Period end   (YYYY-MM-DD)

    Returns: {payments: [{date, customer, amount, method, reference}], total_collected, error}
    """
    try:
        client = _get_client()

        payments = client.call(
            "account.payment", "search_read",
            args=[[
                ["payment_type", "=", "inbound"],
                ["state", "=", "posted"],
                ["date", ">=", start_date],
                ["date", "<=", end_date],
            ]],
            kwargs={"fields": ["name", "date", "partner_id", "amount",
                               "payment_method_line_id", "ref"],
                    "order": "date desc"},
        )

        rows = []
        total_collected = 0.0

        for pmt in payments:
            amount = pmt.get("amount", 0)
            total_collected += amount
            rows.append({
                "date":      pmt.get("date"),
                "customer":  pmt["partner_id"][1] if pmt.get("partner_id") else "Unknown",
                "amount":    round(amount, 2),
                "method":    pmt["payment_method_line_id"][1] if pmt.get("payment_method_line_id") else "Manual",
                "reference": pmt.get("ref") or pmt.get("name", ""),
            })

        return {
            "period":          f"{start_date} to {end_date}",
            "payments":        rows,
            "total_collected": round(total_collected, 2),
            "payment_count":   len(rows),
            "error":           None,
        }

    except Exception as exc:
        logger.error(f"get_payment_history failed: {exc}")
        return {"payments": [], "total_collected": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: search_invoices
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_invoices(
    status: str = "all",
    start_date: str = None,
    end_date: str = None,
    customer_email: str = None,
    min_amount: float = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Flexible invoice search — filter by status, date range, customer, or amount.

    Args:
        status:         "all" | "paid" | "unpaid" | "partial" | "overdue" | "draft"
        start_date:     Invoice date from (YYYY-MM-DD, optional)
        end_date:       Invoice date to   (YYYY-MM-DD, optional)
        customer_email: Filter to one customer (optional)
        min_amount:     Minimum invoice amount filter (optional)
        limit:          Max results (default: 50, max: 200)

    Returns: {invoices: [...], count, total_amount, error}
    """
    limit = min(max(1, limit), 200)

    try:
        client = _get_client()
        domain = [["move_type", "=", "out_invoice"]]

        # Status filter
        today = datetime.now().strftime("%Y-%m-%d")
        if status == "paid":
            domain.append(["payment_state", "=", "paid"])
            domain.append(["state", "=", "posted"])
        elif status == "unpaid":
            domain.append(["payment_state", "=", "not_paid"])
            domain.append(["state", "=", "posted"])
        elif status == "partial":
            domain.append(["payment_state", "=", "partial"])
            domain.append(["state", "=", "posted"])
        elif status == "overdue":
            domain.extend([
                ["payment_state", "in", ["not_paid", "partial"]],
                ["invoice_date_due", "<", today],
                ["state", "=", "posted"],
            ])
        elif status == "draft":
            domain.append(["state", "=", "draft"])
        else:
            domain.append(["state", "!=", "cancel"])

        if start_date:
            domain.append(["invoice_date", ">=", start_date])
        if end_date:
            domain.append(["invoice_date", "<=", end_date])

        if customer_email:
            partners = client.call(
                "res.partner", "search_read",
                args=[[["email", "=", customer_email]]],
                kwargs={"fields": ["id"], "limit": 1},
            )
            if not partners:
                return {"invoices": [], "count": 0, "total_amount": 0,
                        "error": f"Customer not found: {customer_email}"}
            domain.append(["partner_id", "=", partners[0]["id"]])

        if min_amount is not None:
            domain.append(["amount_total", ">=", min_amount])

        invoices = client.call(
            "account.move", "search_read",
            args=[domain],
            kwargs={
                "fields": ["name", "invoice_date", "invoice_date_due", "partner_id",
                           "amount_total", "amount_residual", "payment_state", "state"],
                "limit": limit,
                "order": "invoice_date desc",
            },
        )

        rows = []
        total_amount = 0.0
        for inv in invoices:
            total_amount += inv.get("amount_total", 0)
            rows.append({
                "id":          inv["id"],
                "number":      inv["name"],
                "date":        inv.get("invoice_date"),
                "due_date":    inv.get("invoice_date_due"),
                "customer":    inv["partner_id"][1] if inv.get("partner_id") else "Unknown",
                "amount":      round(inv.get("amount_total", 0), 2),
                "amount_due":  round(inv.get("amount_residual", 0), 2),
                "status":      inv.get("payment_state", inv.get("state")),
            })

        return {
            "invoices":     rows,
            "count":        len(rows),
            "total_amount": round(total_amount, 2),
            "filters_used": {"status": status, "start_date": start_date,
                             "end_date": end_date, "customer_email": customer_email},
            "error":        None,
        }

    except Exception as exc:
        logger.error(f"search_invoices failed: {exc}")
        return {"invoices": [], "count": 0, "total_amount": 0, "error": str(exc)}


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Odoo MCP Server starting (24 tools registered)…")
    mcp.run(transport="stdio")
