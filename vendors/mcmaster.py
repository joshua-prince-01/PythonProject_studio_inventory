from __future__ import annotations

from pathlib import Path

from vendors.base import VendorParser, ParsedOrder, ParsedLineItem

# reuse your existing proven extractors
from Read_Order_Details import extract_order_info_by_page
from Read_Line_Items import parse_receipt


class McMasterParser:
    vendor = "mcmaster"

    def detect(self, pdf_path: Path) -> bool:
        # cheap + reliable: look for 'mcmaster' in filename OR in first page text
        name = pdf_path.name.lower()
        if "mcmaster" in name:
            return True
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as p:
                txt = (p.pages[0].extract_text() or "").lower()
            return ("mcmaster" in txt) or ("mcmaster-carr" in txt)
        except Exception:
            return False

    def parse_order(self, pdf_path: Path, debug: bool = False) -> ParsedOrder:
        info = extract_order_info_by_page(str(pdf_path), debug=debug)
        return ParsedOrder(
            vendor=self.vendor,
            source_file=pdf_path.name,
            pdf_path=str(pdf_path),
            purchase_order=info.purchase_order,
            invoice=str(info.invoice) if info.invoice is not None else None,
            invoice_date=info.invoice_date,
            account_number=info.account_number,
            payment_date=info.payment_date,
            credit_card=info.credit_card,
            merchandise=info.merchandise,
            shipping=info.shipping,
            sales_tax=info.sales_tax,
            total=info.total,
        )

    def parse_line_items(self, pdf_path: Path, debug: bool = False) -> list[ParsedLineItem]:
        order = self.parse_order(pdf_path, debug=debug)
        items = parse_receipt(str(pdf_path), page_num=0, debug=debug)
        out: list[ParsedLineItem] = []
        for d in items:
            out.append(
                ParsedLineItem(
                    vendor=self.vendor,
                    source_file=pdf_path.name,
                    invoice=order.invoice,
                    purchase_order=order.purchase_order,
                    line=d.get("line"),
                    sku=str(d.get("sku") or ""),
                    description=str(d.get("description") or ""),
                    ordered=_to_int(d.get("ordered")),
                    shipped=_to_int(d.get("shipped")),
                    balance=_to_int(d.get("balance")),
                    unit_price=_to_float(d.get("price")),
                    line_total=_to_float(d.get("total")),
                )
            )
        return out


def _to_int(x):
    try:
        if x is None: return None
        s = str(x).strip()
        if s == "": return None
        return int(float(s))
    except Exception:
        return None

def _to_float(x):
    try:
        if x is None: return None
        s = str(x).strip().replace("$","").replace(",","")
        if s == "": return None
        return float(s)
    except Exception:
        return None
