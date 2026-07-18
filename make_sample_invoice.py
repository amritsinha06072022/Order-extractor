"""Generate a realistic sample invoice PDF for testing the extractor."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

styles = getSampleStyleSheet()
right = ParagraphStyle("right", parent=styles["Normal"], alignment=2)
small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

doc = SimpleDocTemplate("sample_invoice.pdf", pagesize=letter,
                        topMargin=0.6 * inch, bottomMargin=0.6 * inch)
story = []

# Header
story.append(Paragraph("<b>NorthPeak Supply Co.</b>", styles["Title"]))
story.append(Paragraph("1420 Industrial Way, Portland, OR 97209 &nbsp;|&nbsp; "
                       "accounts@northpeaksupply.com &nbsp;|&nbsp; (503) 555-0142", small))
story.append(Spacer(1, 18))

# Invoice meta + bill-to, side by side
meta = [
    [Paragraph("<b>Bill To:</b>", styles["Normal"]),
     Paragraph("<b>Invoice</b>", right)],
    [Paragraph("Riverside Cafe &amp; Roastery<br/>"
               "Attn: Maria Delgado<br/>"
               "88 Harbor Street<br/>"
               "Seattle, WA 98101<br/>"
               "maria@riversidecafe.com", styles["Normal"]),
     Paragraph("Invoice #: <b>INV-2026-00847</b><br/>"
               "PO #: PO-5591<br/>"
               "Invoice Date: 2026-07-09<br/>"
               "Due Date: 2026-08-08<br/>"
               "Delivery Date: 2026-07-15<br/>"
               "Terms: Net 30", right)],
]
mt = Table(meta, colWidths=[3.3 * inch, 3.3 * inch])
mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
story.append(mt)
story.append(Spacer(1, 22))

# Line items
rows = [["SKU", "Description", "Qty", "Unit Price", "Amount"],
        ["CB-1201", "Colombia Supremo whole bean coffee, 5 lb bag", "12", "$62.00", "$744.00"],
        ["CB-3300", "Ethiopia Yirgacheffe whole bean coffee, 5 lb bag", "8", "$71.50", "$572.00"],
        ["ML-0450", "Oat milk barista blend, 32 oz (case of 12)", "6", "$38.00", "$228.00"],
        ["CUP-16D", "16 oz double-wall paper cup (sleeve of 500)", "10", "$24.75", "$247.50"],
        ["SYR-VAN", "Vanilla flavor syrup, 1 L bottle", "24", "$9.20", "$220.80"]]
t = Table(rows, colWidths=[0.9 * inch, 3.1 * inch, 0.5 * inch, 1.0 * inch, 1.0 * inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d0da")),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(t)
story.append(Spacer(1, 12))

# Totals
totals = [["Subtotal", "$2,012.30"],
          ["Tax (9.5%)", "$191.17"],
          ["Shipping", "$45.00"],
          ["Total Due (USD)", "$2,248.47"]]
tt = Table(totals, colWidths=[1.5 * inch, 1.0 * inch], hAlign="RIGHT")
tt.setStyle(TableStyle([
    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
]))
story.append(tt)
story.append(Spacer(1, 26))
story.append(Paragraph("Thank you for your business. Please remit payment to the address above "
                       "referencing the invoice number.", small))

doc.build(story)
print("wrote sample_invoice.pdf")