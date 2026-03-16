---
name: create-elegant-gst-invoice
description: Generate a highly polished, production-grade PDF GST invoice. Use this directive when the user needs to create, format, or generate a GST invoice that must look professional, distinctive, and elegant.
---

# Create Elegant GST Invoice

This directive ensures that any generated GST invoice is not just legally compliant, but aesthetically remarkable. It follows the principles of high-end frontend design while adhering to deterministic execution for calculations and PDF generation.

## 1. Goal and Requirements
- **Goal**: Generate a beautiful, mathematically accurate GST invoice PDF that reflects a premium, bold aesthetic direction.
- **Mandatory GST Elements**: Seller Details, Consignee (Ship to), Buyer (Bill to), State Code, GSTIN (all parties).
- **Mandatory Invoice Meta**: Invoice No., e-Way Bill No., Dated, Delivery Note, Mode/Terms of Payment, Reference No., Buyer's Order No., Dispatch Doc No., Dispatched through, Destination, Terms of Delivery.
- **Line Items Structure**: Sl No., Description of Goods, HSN/SAC, Quantity, Rate per, Amount. Tax rows (e.g. OUTPUT IGST@18%) should be clearly associated with their items.
- **Tax Summary Table**: HSN/SAC, Taxable Value, Integrated Tax Rate & Amount, Total Tax Amount.
- **Totals Phase**: Total Invoice Value (in numbers and words for both items and tax amounts), Company PAN, Bank Details, Declaration, Authorized Signature.

## 2. Aesthetic Direction & Design Principles
Before generating the invoice, strictly adhere to the standardized corporate tabular layout (matching `STS-INV-1225-002.pdf`). **Do not use experimental or "luxury" typography.**

- **Typography**: Strictly use standard sans-serif system fonts (`Arial, Helvetica, sans-serif`). Ensure all text is highly legible and concise.
- **Color & Theme**: Stick to a strictly monochrome black-and-white palette. Use `1px solid black` for all grids and borders.
- **Spatial Composition**: Maintain a rigid, boxified structure. Tighten paddings and margins to ensure maximum data density without overflowing the A4 page height. The layout should have distinct blocks for Seller, Consignee, and Buyer side-by-side using CSS grid.
- **Visual Refinement**: Ensure all nested tables (like the Tax Summary) align perfectly with their outer boundaries. Use bold font weights (`font-weight: bold`) to distinguish headers and labels from values.

## 3. Execution Workflow
You sit between intent (designing the HTML) and execution (generating the PDF). Your job is to orchestrate:

1. **Calculate**: Calculate all values (line item totals, subtotals, tax brackets, grand totals).
2. **Fetch Default Company Profile**: Ensure the system uses the default company profile (boolean `is_default=true` in `company_profile` table) as the seller for the invoice unless explicitly overridden.
3. **Design HTML**: Write a self-contained HTML/CSS string reflecting the BOLD aesthetics above. Inject the calculated values deterministically.
4. **Execute**: Call a deterministic Python script in the `execution/` directory to convert the HTML string/file into a final PDF.
    - **Check for Tools**: Look for a script like `execution/html_to_pdf.py` first.
    - **Self-Anneal**: If no such script exists, create it using a reliable library (e.g., `weasyprint`, `pdfkit`/`wkhtmltopdf`, or headless `playwright`). Ensure the script accepts an HTML file path and an output PDF path.
4. **Deliver**: Place the final PDF format in the `.tmp/` directory before finalizing or offering to move it to a client-deliverable directory (or immediately display/share it with the user).

## 4. Edge Cases & Constraints
- **Multi-page invoices**: Ensure the HTML/CSS handles page breaks cleanly. Use `@page` CSS directives to manage margins and repeat table headers (`thead { display: table-header-group; }`).
- **Precision**: Financial numbers MUST have exactly two decimal places.
- **Word Conversion**: Provide an accurate number-to-words conversion for the final total (Indian Numbering System by default, unless otherwise specified).
