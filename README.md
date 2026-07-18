# Order Extractor

Turn invoice / order **PDFs** or plain-text **order emails** into clean,
structured **JSON** and **CSV** using the Claude API.

For every file it pulls out the customer, supplier, order metadata (order
number, PO number, dates, currency, totals) and every line item (SKU,
description, quantity, unit price, line total).

## What's in here

| File | Purpose |
|------|---------|
| `extract_orders.py` | The extractor. This is the thing you run. |
| `sample_invoice.pdf` | A realistic sample invoice to test on. |
| `sample_order_email.txt` | A sample order email (shows the text/email path). |
| `make_sample_invoice.py` | Regenerates the sample PDF (optional). |
| `requirements.txt` | Dependencies. |

## Features
- **Automated Extraction:** Uses LLM-based parsing to identify key entities (items, prices, shipping addresses).
- **Structured Output:** Easily exports data to JSON and CSV for integration into other systems.
- **Modular Design:** Separates API communication from data processing logic.

## Prerequisites
- Python 3.10
- An active Anthropic API Key.

## Setup

```bash
pip install -r requirements.txt
```

Then open `extract_orders.py` and paste your Anthropic API key into the `KEY`
variable near the top:

```python
KEY = "sk-ant-..."
```

Prefer not to hard-code it? Leave `KEY = ""` and set an environment variable
instead:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

```bash
# One file
python extract_orders.py sample_invoice.pdf

# Several files at once (PDFs and emails can be mixed)
python extract_orders.py sample_invoice.pdf sample_order_email.txt

# A whole folder of orders
python extract_orders.py ./inbox/

# Choose where output goes (default is ./output)
python extract_orders.py sample_invoice.pdf -o results
```

## Output

Everything lands in the `output/` folder (or whatever you pass to `-o`):

- `<name>.json` — the full structured record for each file
- `<name>.csv` — one row per line item, with order/customer fields repeated
- `all_line_items.csv` — every line item from every file, combined (drop this
  straight into a spreadsheet or database)

Example JSON shape:

```json
{
  "order": {
    "order_number": "INV-2026-00847",
    "order_date": "2026-07-09",
    "currency": "USD",
    "total": 2248.47
  },
  "customer": { "company": "Riverside Cafe & Roastery", "email": "maria@riversidecafe.com" },
  "supplier": { "name": "NorthPeak Supply Co." },
  "line_items": [
    { "sku": "CB-1201", "description": "Colombia Supremo whole bean coffee, 5 lb bag",
      "quantity": 12, "unit_price": 62.0, "line_total": 744.0 }
  ]
}
```

## How it works

The script sends each document to Claude and forces a **tool call** whose input
schema is the order structure. Because the model must respond by "calling"
that tool, every response is valid JSON in exactly the shape defined by
`ORDER_SCHEMA` — no fragile parsing of free text. PDFs are sent natively (Claude
reads the layout, tables and totals directly); emails are sent as text.

## Customising what gets extracted

Edit `ORDER_SCHEMA` in `extract_orders.py` — add, remove or rename fields and
the model will follow. If you add top-level fields you'll also want to map them
into `CSV_COLUMNS` / `flatten_rows` for the CSV output.

## Notes

- **Model:** defaults to `claude-sonnet-4-6` (cost-efficient, strong at
  extraction). For unusually messy documents switch `MODEL` to
  `claude-opus-4-8`; for the newest Sonnet use `claude-sonnet-5`.
- **Scanned PDFs:** Claude reads image-based PDFs too, so scans generally work
  without a separate OCR step.
- **Large PDFs:** files over ~20 MB should go through the Files API rather than
  inline base64. Ask if you want that variant.
- **Cost:** each PDF page is roughly 1,500–3,000 input tokens plus a small
  output cost per document.
