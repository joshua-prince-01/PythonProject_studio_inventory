from __future__ import annotations

from typing import Sequence
from vendors.base import VendorParser

from vendors.mcmaster import McMasterParser
from vendors.digikey import DigiKeyParser
from vendors.mouser import MouserParser
from vendors.newark import NewarkParser
from vendors.arduino import ArduinoParser
from vendors.bambulab import BambuLabParser


def all_parsers() -> Sequence[VendorParser]:
    # Order matters: put the most distinctive first if you later add overlaps
    return [
        McMasterParser(),
        DigiKeyParser(),
        MouserParser(),
        NewarkParser(),
        ArduinoParser(),
        BambuLabParser(),
    ]


def pick_parser(pdf_path):
    for p in all_parsers():
        try:
            if p.detect(pdf_path):
                return p
        except Exception:
            continue
    return None
