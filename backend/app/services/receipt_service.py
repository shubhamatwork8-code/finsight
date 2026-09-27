import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PIL import Image

from app.core.errors import AppError
from app.core.money import money
from app.utils.validators import LEDGER_CURRENCIES

MAX_RECEIPT_BYTES = 8 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
_TOTAL_PHRASES = ("grand total", "amount due", "balance due", "total due", "amount paid", "total")
_IGNORE_PHRASES = ("subtotal", "sub-total", "sub total", "sales tax", "tax", "vat", "gst", "tip", "discount")
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}
_TOKEN = re.compile(
    r"(?:(?P<code>USD|EUR|GBP|INR|AED|SGD|AUD|CAD|CHF|JPY)|(?P<sym>[$€£₹¥]))?\s*(?P<num>\d[\d.,]*\d|\d)",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_SLASH_DATE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_NAMED_DATE = re.compile(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b")
_OCR = None


def parse_receipt_text(text: str, ledger_currency: str, *, source: str) -> dict:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    amount, detected_currency, amount_line = _choose_amount(lines)
    occurred_at, assumed_time, ambiguous_date = _choose_date(text or "")
    merchant = _merchant(lines)
    warnings: list[str] = []
    if source == "ocr":
        warnings.append("Text was read from a photo or scan. Confirm the amount and merchant before posting.")
    if source == "unreadable" or not lines:
        warnings.append("No readable text was found. Enter the bill details yourself.")
    if amount is None:
        warnings.append("No total was found. Enter the amount to post.")
    if not merchant:
        warnings.append("No merchant name was found.")
    if occurred_at is None:
        warnings.append("No date was found. Enter when this bill was paid.")
    elif assumed_time:
        warnings.append("The bill had a date without a time. The time is set to 12:00 UTC.")
    if ambiguous_date:
        warnings.append("The date order was ambiguous. Confirm the date.")
    ledger = (ledger_currency or "USD").upper()
    if detected_currency and detected_currency != ledger:
        warnings.append(
            f"The bill shows {detected_currency}, while this ledger uses {ledger}. Enter the amount in {ledger}. It is not converted automatically."
        )
    description = "Imported from receipt"
    if amount_line and merchant and amount_line.lower() != merchant.lower():
        description = amount_line[:160]
    return {
        "source": source,
        "merchant": merchant,
        "amount": format(amount, "f") if amount is not None else "",
        "detected_currency": detected_currency or "",
        "ledger_currency": ledger,
        "timestamp": occurred_at.isoformat(timespec="minutes") if occurred_at else "",
        "transaction_type": "DEBIT",
        "category": "Uncategorized",
        "description": description,
        "warnings": warnings,
        "raw_text": (text or "")[:4000],
    }


def extract_receipt(filename: str, data: bytes, ledger_currency: str) -> dict:
    if not data:
        raise AppError("INVALID_RECEIPT", "The receipt file is empty.")
    if len(data) > MAX_RECEIPT_BYTES:
        raise AppError("INVALID_RECEIPT", "Receipt files must be 8 MB or smaller.")
    suffix = _suffix(filename)
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError("INVALID_RECEIPT", "Upload a PDF, PNG, JPG, or WEBP receipt.")
    text, source = _read_document(suffix, data)
    draft = parse_receipt_text(text, ledger_currency, source=source)
    draft["filename"] = filename or "receipt"
    return draft


def _suffix(filename: str) -> str:
    name = (filename or "").lower().strip()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""


def _read_document(suffix: str, data: bytes) -> tuple[str, str]:
    try:
        if suffix == ".pdf":
            text = _pdf_text(data)
            if len(text.strip()) >= 12:
                return text, "pdf_text"
            scanned = _pdf_ocr(data)
            return (scanned, "ocr") if scanned.strip() else (text, "unreadable")
        image = Image.open(io.BytesIO(data))
        image.load()
        text = _ocr_image(image)
        return (text, "ocr") if text.strip() else ("", "unreadable")
    except AppError:
        raise
    except Exception:
        return "", "unreadable"


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:3])


def _pdf_ocr(data: bytes) -> str:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    parts: list[str] = []
    try:
        for index in range(min(len(document), 3)):
            page = document[index]
            bitmap = page.render(scale=2)
            try:
                parts.append(_ocr_image(bitmap.to_pil()))
            finally:
                bitmap.close()
                page.close()
    finally:
        document.close()
    return "\n".join(part for part in parts if part.strip())


def _ocr_image(image: Image.Image) -> str:
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR

        _OCR = RapidOCR()
    import numpy as np

    result, _elapsed = _OCR(np.array(image.convert("RGB")))
    if not result:
        return ""
    return "\n".join(str(item[1]) for item in result if len(item) > 1)


def _choose_amount(lines: list[str]) -> tuple[Decimal | None, str, str]:
    ranked: list[tuple[int, int, Decimal, str, str]] = []
    fallback: list[tuple[int, Decimal, str, str]] = []
    for index, line in enumerate(lines):
        lower = line.lower()
        if any(phrase in lower for phrase in _IGNORE_PHRASES) and "total" not in lower.replace("subtotal", "").replace("sub-total", "").replace("sub total", ""):
            continue
        if "subtotal" in lower or "sub-total" in lower or "sub total" in lower:
            continue
        rank = next((position for position, phrase in enumerate(_TOTAL_PHRASES) if phrase in lower), None)
        for amount, code in _amounts_on_line(line):
            if rank is None:
                fallback.append((index, amount, code, line))
            else:
                ranked.append((rank, index, amount, code, line))
    if ranked:
        ranked.sort(key=lambda item: (item[0], -item[1]))
        _rank, _index, amount, code, line = ranked[0]
        return amount, code, line
    with_cents = [item for item in fallback if item[1] != item[1].to_integral_value()]
    chosen = (with_cents or fallback)
    if not chosen:
        return None, "", ""
    _index, amount, code, line = chosen[-1]
    return amount, code, line


def _amounts_on_line(line: str) -> list[tuple[Decimal, str]]:
    found: list[tuple[Decimal, str]] = []
    for match in _TOKEN.finditer(line):
        code = (match.group("code") or "").upper()
        symbol = match.group("sym") or ""
        if symbol:
            code = _SYMBOLS.get(symbol, code)
        number = _number(match.group("num"))
        if number is None:
            continue
        if not code and number == number.to_integral_value() and 1900 <= number <= 2100:
            continue
        if number <= 0 or number >= Decimal("1000000000"):
            continue
        if code and code not in LEDGER_CURRENCIES:
            code = ""
        found.append((money(number), code))
    return found


def _number(raw: str) -> Decimal | None:
    text = raw.strip()
    if not text or not text[0].isdigit():
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        tail = text.split(",")[-1]
        text = text.replace(",", ".") if len(tail) == 2 else text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _choose_date(text: str) -> tuple[datetime | None, bool, bool]:
    named = _NAMED_DATE.search(text)
    if named:
        month = _MONTHS.get(named.group(1).lower())
        if month:
            parsed = _safe_date(int(named.group(3)), month, int(named.group(2)))
            if parsed:
                return parsed, True, False
    iso = _ISO_DATE.search(text)
    if iso:
        parsed = _safe_date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        if parsed:
            return parsed, True, False
    slash = _SLASH_DATE.search(text)
    if slash:
        first = int(slash.group(1))
        second = int(slash.group(2))
        year = int(slash.group(3))
        if year < 100:
            year += 2000
        ambiguous = first <= 12 and second <= 12
        if first > 12:
            parsed = _safe_date(year, second, first)
        else:
            parsed = _safe_date(year, first, second)
        if parsed:
            return parsed, True, ambiguous
    return None, False, False


def _safe_date(year: int, month: int, day: int) -> datetime | None:
    try:
        return datetime(year, month, day, 12, 0)
    except ValueError:
        return None


def _merchant(lines: list[str]) -> str:
    for line in lines:
        lower = line.lower()
        if lower in {"invoice", "receipt", "tax invoice", "bill", "statement"}:
            continue
        if _ISO_DATE.search(line) or _SLASH_DATE.search(line) or _NAMED_DATE.search(line):
            if sum(char.isalpha() for char in line) < 8:
                continue
        letters = sum(char.isalpha() for char in line)
        if letters < 3:
            continue
        if _amounts_on_line(line) and letters < 6:
            continue
        return line[:80]
    return ""
