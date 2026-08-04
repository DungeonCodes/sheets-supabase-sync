from __future__ import annotations

import re
from urllib.parse import urlparse


def extract_spreadsheet_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in {"docs.google.com", "sheets.google.com"}:
        raise ValueError("URL de planilha invalida")
    match = re.fullmatch(r"/spreadsheets/d/([A-Za-z0-9_-]{10,})/(?:edit|view).*", parsed.path)
    if not match:
        raise ValueError("URL de planilha invalida")
    return match.group(1)
