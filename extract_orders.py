#!/usr/bin/env python3
"""
extract_orders.py
=================
Turn invoice / order PDFs (or plain-text order emails) into clean, structured
JSON and CSV using the Claude API.

Usage
-----
    python extract_orders.py sample_invoice.pdf
    python extract_orders.py invoice1.pdf order_email.txt invoice2.pdf
    python extract_orders.py ./inbox/          # every .pdf/.txt/.eml in a folder

For each input file it writes two siblings next to your chosen output dir:
    <name>.json   full structured record
    <name>.csv    one row per line item (order/customer fields repeated)

It also writes an `all_line_items.csv` combining every file processed, which is
usually what you want to drop into a spreadsheet or database.

The API key
-----------
Set up the API key with your key in the environment variables as shown in the setup. Do not paste it in this code.
"""

import argparse
import base64
import csv
import json
import os
import sys
from pathlib import Path

import anthropic

KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Which model to use. Sonnet is the cost-efficient default and is plenty strong
# for document extraction. Swap to "claude-opus-4-8" for the hardest documents,
# or "claude-sonnet-5" for the newest Sonnet.
MODEL = "claude-sonnet-4-6"

PDF_SUFFIXES = {".pdf"}
TEXT_SUFFIXES = {".txt", ".eml", ".md", ".text"}
SUPPORTED = PDF_SUFFIXES | TEXT_SUFFIXES

# ---------------------------------------------------------------------------
# The extraction schema. We hand this to Claude as a *tool* and force the model
# to call it, so every response is valid JSON in exactly this shape. Add or
# remove fields here to change what gets pulled out — no prompt changes needed.
# ---------------------------------------------------------------------------
ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "order": {
            "type": "object",
            "properties": {
                "order_number": {"type": ["string", "null"],
                                 "description": "Invoice or order number, e.g. INV-2026-00847"},
                "purchase_order_number": {"type": ["string", "null"]},
                "order_date": {"type": ["string", "null"],
                               "description": "Order/invoice date as ISO YYYY-MM-DD"},
                "due_date": {"type": ["string", "null"], "description": "ISO YYYY-MM-DD"},
                "delivery_date": {"type": ["string", "null"], "description": "ISO YYYY-MM-DD"},
                "currency": {"type": ["string", "null"], "description": "ISO code, e.g. USD"},
                "subtotal": {"type": ["number", "null"]},
                "tax": {"type": ["number", "null"]},
                "shipping": {"type": ["number", "null"]},
                "total": {"type": ["number", "null"]},
            },
            "required": ["order_number", "order_date", "total"],
        },
        "customer": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "Contact person, if any"},
                "company": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "billing_address": {"type": ["string", "null"], "description": "Single line"},
                "shipping_address": {"type": ["string", "null"], "description": "Single line"},
            },
            "required": ["company"],
        },
        "supplier": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "Seller / vendor issuing the document"},
                "email": {"type": ["string", "null"]},
            },
            "required": ["name"],
        },
        "line_items": {
            "type": "array",
            "description": "One entry per product line on the order.",
            "items": {
                "type": "object",
                "properties": {
                    "sku": {"type": ["string", "null"], "description": "Product/SKU/item code"},
                    "description": {"type": ["string", "null"]},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "line_total": {"type": ["number", "null"]},
                },
                "required": ["description", "quantity"],
            },
        },
    },
    "required": ["order", "customer", "line_items"],
}

TOOL = {
    "name": "record_order",
    "description": "Record the structured order/invoice data extracted from the document.",
    "input_schema": ORDER_SCHEMA,
}

SYSTEM_PROMPT = (
    "You extract structured order data from invoices, purchase orders and order "
    "emails. Read the document carefully and call the record_order tool exactly "
    "once with everything you find. Rules: copy values verbatim from the "
    "document; never invent data — use null for anything genuinely absent. "
    "Normalise all dates to ISO YYYY-MM-DD. Strip currency symbols and thousands "
    "separators from numeric fields so they parse as plain numbers (e.g. "
    "$2,248.47 -> 2248.47). Capture every line item, including ones that span "
    "multiple text lines."
)

# Flat column order for the CSV output (one row per line item).
CSV_COLUMNS = [
    "source_file",
    "supplier_name",
    "order_number", "purchase_order_number", "order_date", "due_date",
    "delivery_date", "currency",
    "customer_company", "customer_name", "customer_email", "customer_phone",
    "billing_address", "shipping_address",
    "sku", "item_description", "quantity", "unit_price", "line_total",
    "order_subtotal", "order_tax", "order_shipping", "order_total",
]


def build_client() -> anthropic.Anthropic:
    api_key = KEY.strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit(
            "No API key found. Paste it into the KEY variable at the top of "
            "extract_orders.py, or set the ANTHROPIC_API_KEY environment variable."
        )
    return anthropic.Anthropic(api_key=api_key)


def build_content(path: Path):
    """Build the user-message content block for a PDF or a text file."""
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        document = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": data},
        }
        return [document, {"type": "text", "text": "Extract the order data from this document."}]
    # Plain-text / email input
    text = path.read_text(encoding="utf-8", errors="replace")
    return [{"type": "text",
             "text": "Extract the order data from this order/email text:\n\n" + text}]


def extract_one(client: anthropic.Anthropic, path: Path) -> dict:
    """Call the API and return the structured record for a single file."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_order"},  # force structured output
        messages=[{"role": "user", "content": build_content(path)}],
    )
    for block in message.content:
        if block.type == "tool_use" and block.name == "record_order":
            return block.input
    raise RuntimeError(f"Model did not return structured data for {path.name}")


def flatten_rows(record: dict, source_file: str) -> list[dict]:
    """Turn one structured record into one CSV row per line item."""
    order = record.get("order") or {}
    customer = record.get("customer") or {}
    supplier = record.get("supplier") or {}
    items = record.get("line_items") or [{}]  # keep a row even if no items found

    base = {
        "source_file": source_file,
        "supplier_name": supplier.get("name"),
        "order_number": order.get("order_number"),
        "purchase_order_number": order.get("purchase_order_number"),
        "order_date": order.get("order_date"),
        "due_date": order.get("due_date"),
        "delivery_date": order.get("delivery_date"),
        "currency": order.get("currency"),
        "customer_company": customer.get("company"),
        "customer_name": customer.get("name"),
        "customer_email": customer.get("email"),
        "customer_phone": customer.get("phone"),
        "billing_address": customer.get("billing_address"),
        "shipping_address": customer.get("shipping_address"),
        "order_subtotal": order.get("subtotal"),
        "order_tax": order.get("tax"),
        "order_shipping": order.get("shipping"),
        "order_total": order.get("total"),
    }
    rows = []
    for item in items:
        row = dict(base)
        row.update({
            "sku": item.get("sku"),
            "item_description": item.get("description"),
            "quantity": item.get("quantity"),
            "unit_price": item.get("unit_price"),
            "line_total": item.get("line_total"),
        })
        rows.append(row)
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def collect_inputs(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(c for c in p.iterdir() if c.suffix.lower() in SUPPORTED))
        elif p.suffix.lower() in SUPPORTED:
            files.append(p)
        else:
            print(f"  skipping unsupported file: {p}", file=sys.stderr)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured orders from PDFs / emails.")
    parser.add_argument("inputs", nargs="+", help="PDF/txt/eml files or a folder of them")
    parser.add_argument("-o", "--out-dir", default="output", help="output directory (default: output)")
    args = parser.parse_args()

    files = collect_inputs(args.inputs)
    if not files:
        sys.exit("No supported input files found (.pdf, .txt, .eml).")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = build_client()

    all_rows: list[dict] = []
    for path in files:
        print(f"Extracting {path.name} ...")
        try:
            record = extract_one(client, path)
        except Exception as e:  # noqa: BLE001 - report and keep going through the batch
            print(f"  ! failed: {e}", file=sys.stderr)
            continue

        stem = path.stem
        (out_dir / f"{stem}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        rows = flatten_rows(record, path.name)
        write_csv(rows, out_dir / f"{stem}.csv")
        all_rows.extend(rows)

        n_items = len(record.get("line_items") or [])
        order_no = (record.get("order") or {}).get("order_number") or "?"
        print(f"  -> {stem}.json + {stem}.csv  (order {order_no}, {n_items} line items)")

    if all_rows:
        write_csv(all_rows, out_dir / "all_line_items.csv")
        print(f"\nDone. {len(all_rows)} line items across {len(files)} file(s).")
        print(f"Combined CSV: {out_dir / 'all_line_items.csv'}")


if __name__ == "__main__":
    main()
