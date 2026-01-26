from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pdfplumber


# -------------------------------------------------
# Detection
# -------------------------------------------------

def detect(pdf_path: str) -> bool:
    with pdfplumber.open(pdf_path) as pdf:
        txt = (pdf.pages[0].extract_text() or "").upper()
    return "DIGI-KEY ELECTRONICS" in txt


# -------------------------------------------------
# Order-level parsing
# -------------------------------------------------

def parse_order(pdf_path: str, debug: bool = False) -> dict:
    text = _all_text(pdf_path)

    po_ack = _find(r"PO Acknowledgement\s+(\d+)", text)
    web_id = _find(r"WEB ORDER ID:\s*(\d+)", text)

    order_date = _find(r"Order Date:\s*([0-9\-A-Z]+)", text)

    sales = _money_after("Sales Amount", text)
    shipping = _money_after("Shipping charges applied", text)
    tax = _money_after("Sales Tax", text)
    total = _money_after("Total", text)

    if debug:
        print("\n[DIGIKEY ORDER]")
        print("  po_ack:", po_ack)
        print("  web_id:", web_id)
        print("  sales:", sales)
        print("  shipping:", shipping)
        print("  tax:", tax)
        print("  total:", total)

    return {
        "vendor": "digikey",
        "invoice": po_ack,
        "purchase_order": web_id,
        "invoice_date": order_date,
        "account_number": None,
        "payment_date": None,
        "credit_card": None,
        "merchandise": sales,
        "shipping": shipping,
        "sales_tax": tax,
        "total": total,
    }


# -------------------------------------------------
# Line-item parsing
# -------------------------------------------------

PART_RE = re.compile(
    r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+PART:\s*([A-Z0-9\-]+)"
)

PRICE_RE = re.compile(r"(\d+\.\d{2})\s+(\d+\.\d{2})$")


def parse_line_items(pdf_path: str, debug: bool = False) -> list[dict]:
    lines = _all_text(pdf_path).splitlines()

    items = []
    current = None

    for ln in lines:
        ln = ln.strip()

        # Start of new item
        m = PART_RE.match(ln)
        if m:
            if current:
                items.append(current)

            current = {
                "line": int(m.group(1)),
                "ordered": int(m.group(2)),
                "shipped": int(m.group(3)),
                "balance": int(m.group(4)),
                "sku": m.group(5),
                "description": "",
                "price": None,
                "total": None,
            }
            continue

        if current is None:
            continue

        # Description line
        if ln.startswith("DESC:"):
            desc = ln.replace("DESC:", "").strip()
            pm = PRICE_RE.search(desc)
            if pm:
                current["price"] = float(pm.group(1))
                current["total"] = float(pm.group(2))
                desc = desc[: pm.start()].strip()
            current["description"] = desc
            continue

        # Stop if totals section starts
        if ln.startswith("Sales Amount") or ln.startswith("Total"):
            break

    if current:
        items.append(current)

    if debug:
        print(f"[DIGIKEY] parsed {len(items)} items")

    return items


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _all_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _find(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None


def _money_after(label: str, text: str) -> Optional[float]:
    m = re.search(label + r"\s*([0-9]+\.[0-9]{2})", text, re.I)
    return float(m.group(1)) if m else None
