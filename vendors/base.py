from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Iterable, Optional, Any


@dataclass
class ParsedOrder:
    vendor: str
    source_file: str
    pdf_path: str

    purchase_order: Optional[str] = None
    invoice: Optional[str] = None
    invoice_date: Any = None
    account_number: Optional[str] = None

    payment_date: Any = None
    credit_card: Optional[str] = None

    merchandise: Optional[float] = None
    shipping: Optional[float] = None
    sales_tax: Optional[float] = None
    total: Optional[float] = None


@dataclass
class ParsedLineItem:
    vendor: str
    source_file: str
    invoice: Optional[str]
    purchase_order: Optional[str]

    line: Optional[int]
    sku: str
    description: str

    ordered: Optional[int] = None
    shipped: Optional[int] = None
    balance: Optional[int] = None

    unit_price: Optional[float] = None
    line_total: Optional[float] = None

    # Optional vendor-specific extras
    manufacturer: Optional[str] = None
    mfg_part: Optional[str] = None
    url: Optional[str] = None


class VendorParser(Protocol):
    """A thin strategy interface: each vendor implements these."""

    vendor: str

    def detect(self, pdf_path: Path) -> bool:
        """Return True if this parser can handle the PDF."""
        ...

    def parse_order(self, pdf_path: Path, debug: bool = False) -> ParsedOrder:
        ...

    def parse_line_items(self, pdf_path: Path, debug: bool = False) -> list[ParsedLineItem]:
        ...
