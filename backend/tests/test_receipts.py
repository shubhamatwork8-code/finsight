import io

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.receipt_service import extract_receipt, parse_receipt_text


def test_receipt_text_uses_total_not_tax():
    text = "\n".join(
        [
            "Northwind Cafe",
            "March 2, 2026",
            "Espresso 4.50",
            "Sales tax 0.40",
            "Subtotal 4.50",
            "Total $18.40",
        ]
    )
    draft = parse_receipt_text(text, "USD", source="pdf_text")
    assert draft["merchant"] == "Northwind Cafe"
    assert draft["amount"] == "18.40"
    assert draft["detected_currency"] == "USD"
    assert draft["timestamp"] == "2026-03-02T12:00"
    assert draft["transaction_type"] == "DEBIT"
    assert any("12:00 UTC" in warning for warning in draft["warnings"])


def test_receipt_currency_mismatch_is_a_warning():
    draft = parse_receipt_text("Harbor Books\nTotal EUR 12.00\n2026-04-01", "USD", source="pdf_text")
    assert draft["amount"] == "12.00"
    assert draft["detected_currency"] == "EUR"
    assert any("not converted" in warning for warning in draft["warnings"])


def test_pdf_text_extraction():
    payload = extract_receipt("bill.pdf", _pdf_with_text("Blue Bottle\nTotal $9.75\n2026-05-04"), "USD")
    assert payload["source"] == "pdf_text"
    assert payload["merchant"] == "Blue Bottle"
    assert payload["amount"] == "9.75"
    assert payload["filename"] == "bill.pdf"


def test_image_ocr_reads_a_simple_bill():
    payload = extract_receipt("bill.png", _bill_image(), "USD")
    assert payload["source"] == "ocr"
    assert "18.40" in payload["amount"] or "18.40" in payload["raw_text"]
    assert "Cafe" in payload["raw_text"] or payload["merchant"]


def test_confirm_receipt_posts_to_the_account(client, db):
    from decimal import Decimal

    from app.services.transaction_service import create_account

    account = create_account(db, name="Receipt Checking", account_type="CHECKING", currency="USD", opening_balance=Decimal("50"))
    response = client.post(
        "/api/transactions/receipts/confirm",
        json={
            "account_id": account.id,
            "transaction_type": "DEBIT",
            "amount": "18.40",
            "currency": "USD",
            "merchant": "Northwind Cafe",
            "category": "Uncategorized",
            "description": "Imported from receipt",
            "timestamp": "2026-03-02T12:00:00",
            "source_filename": "cafe.png",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["merchant"] == "Northwind Cafe"
    assert body["amount"] == "18.40"


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    resources = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    lines = ["BT", "/F1 12 Tf"]
    y = 740
    for line in text.splitlines():
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        lines.append(f"1 0 0 1 72 {y} Tm ({safe}) Tj")
        y -= 18
    lines.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(lines).encode())
    contents = writer._add_object(stream)
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = contents
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _bill_image() -> bytes:
    image = Image.new("RGB", (1000, 420), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
    draw.text((40, 40), "Northwind Cafe", fill="black", font=font)
    draw.text((40, 150), "March 2, 2026", fill="black", font=font)
    draw.text((40, 260), "Total $18.40", fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
