import sqlite3
import asyncio
import os
from jinja2 import Environment, FileSystemLoader
from num2words import num2words

class InvoiceRenderer:
    def __init__(self, template_dir='Templates', template_file='gst_invoice.html'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Custom Jinja2 filter: Indian number format (e.g. 1,00,000.00)
        self.env.filters['in_format'] = self._indian_format
        self.template = self.env.get_template(template_file)

    @staticmethod
    def _indian_format(value):
        """Format a number in Indian comma style: 1,00,000.00"""
        try:
            value = float(value)
            integer_part = int(value)
            decimal_part = round((value - integer_part) * 100)
            s = str(integer_part)
            # Indian grouping: last 3 digits, then every 2
            if len(s) > 3:
                result = s[-3:]
                s = s[:-3]
                while s:
                    result = s[-2:] + ',' + result
                    s = s[:-2]
            else:
                result = s
            return f"{result}.{decimal_part:02d}"
        except (ValueError, TypeError):
            return str(value)

    def amount_to_words(self, amount):
        """Converts amount to Indian Rupee word format."""
        try:
            integer_part = int(amount)
            decimal_part = int(round((amount - integer_part) * 100))
            
            words = num2words(integer_part, lang='en_IN').replace(',', '').title()
            result = f"INR {words} Rupees"
            
            if decimal_part > 0:
                decimal_words = num2words(decimal_part, lang='en_IN').title()
                result += f" And {decimal_words} Paise"
            
            return result + " Only"
        except Exception as e:
            print(f"Error converting amount to words: {e}")
            return str(amount)

    def calculate_totals(self, data):
        """Ensures all totals are computed correctly for the template."""
        items = data.get('items', [])
        total_taxable = 0
        total_tax = 0
        total_qty = 0
        
        # Place of Supply Logic: Compare Seller State vs Consignee/Buyer State
        seller_state = data.get('company', {}).get('state_code')
        # We prioritize Consignee (Ship-To) for tax calculation if available, otherwise Bill-To
        supply_state = data.get('consignee', {}).get('state_code') or data.get('buyer', {}).get('state_code')
        
        is_igst = seller_state != supply_state
        data['is_igst'] = is_igst
        
        tax_summary = {} # key by HSN
        
        for item in items:
            total_taxable += item['taxable_value']
            total_tax += item['tax_amount']
            total_qty += item['quantity']
            
            hsn = item['hsn_sac']
            if hsn not in tax_summary:
                tax_summary[hsn] = {
                    'hsn_sac': hsn,
                    'taxable_value': 0,
                    'igst_rate': 0, 'igst_amount': 0,
                    'cgst_rate': 0, 'cgst_amount': 0,
                    'sgst_rate': 0, 'sgst_amount': 0,
                    'total_tax_amount': 0
                }
            
            ts = tax_summary[hsn]
            ts['taxable_value'] += item['taxable_value']
            ts['total_tax_amount'] += item['tax_amount']
            
            if is_igst:
                ts['igst_rate'] = item.get('igst_rate', 0)
                ts['igst_amount'] += item['tax_amount']
            else:
                ts['cgst_rate'] = item.get('cgst_rate', 0)
                ts['sgst_rate'] = item.get('sgst_rate', 0)
                ts['cgst_amount'] += item.get('tax_amount', 0) / 2
                ts['sgst_amount'] += item.get('tax_amount', 0) / 2
        
        data['totals'] = {
            'taxable_value': total_taxable,
            'total_tax_amount': total_tax,
            'grand_total': total_taxable + total_tax,
            'total_quantity': f"{total_qty} {items[0]['unit']}" if items else "0",
            'igst_amount': total_tax if is_igst else 0,
            'cgst_amount': total_tax / 2 if not is_igst else 0,
            'sgst_amount': total_tax / 2 if not is_igst else 0
        }
        
        data['tax_summary'] = list(tax_summary.values())
        data['grand_total_words'] = self.amount_to_words(data['totals']['grand_total'])
        data['tax_amount_words'] = self.amount_to_words(data['totals']['total_tax_amount'])
        
        # Calculate empty rows to fill page
        num_items = len(items)
        total_desired_rows = 14
        empty_rows_count = max(6, total_desired_rows - num_items)
        
        # Determine tax labels to show as standalone rows
        standalone_tax_rows = []
        if is_igst:
            standalone_tax_rows.append({
                "description": "OUTPUT IGST",
                "amount": data['totals']['igst_amount'],
                "tax_rate": items[0].get('igst_rate', 18), # Default fallback to 18 if missing
                "tax_percent_symbol": "%"
            })
        else:
            standalone_tax_rows.append({
                "description": "OUTPUT CGST",
                "amount": data['totals']['cgst_amount'],
                "tax_rate": items[0].get('cgst_rate', 9),
                "tax_percent_symbol": "%"
            })
            standalone_tax_rows.append({
                "description": "OUTPUT SGST",
                "amount": data['totals']['sgst_amount'],
                "tax_rate": items[0].get('sgst_rate', 9),
                "tax_percent_symbol": "%"
            })

        empty_rows = []
        for i in range(empty_rows_count):
            empty_rows.append({"description": "&nbsp;", "amount": None})
        
        target_row_index = 4 # Row 5
        relative_index = target_row_index - num_items
        insert_at = max(0, relative_index)
        
        for tax_row in standalone_tax_rows:
            if insert_at < len(empty_rows):
                empty_rows[insert_at] = {
                    "description": tax_row['description'],
                    "amount": f"{tax_row['amount']:,.2f}",
                    "tax_rate": tax_row['tax_rate'],
                    "tax_percent_symbol": tax_row['tax_percent_symbol'],
                    "is_tax_label": True
                }
                insert_at += 1
            else:
                empty_rows.append({
                    "description": tax_row['description'],
                    "amount": f"{tax_row['amount']:,.2f}",
                    "tax_rate": tax_row['tax_rate'],
                    "tax_percent_symbol": tax_row['tax_percent_symbol'],
                    "is_tax_label": True
                })
        
        data['empty_rows_data'] = empty_rows
        return data

    def render(self, data, output_path):
        data = self.calculate_totals(data)
        html_content = self.template.render(**data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_path

def fetch_invoice_data(db_path, invoice_id=None):
    """Queries the SQLite database for a full invoice data structure."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the latest invoice if no ID provided
    if not invoice_id:
        cursor.execute("SELECT id FROM invoices ORDER BY invoice_date DESC LIMIT 1")
        row = cursor.fetchone()
        if not row: return None
        invoice_id = row['id']

    # 1. Fetch Invoice Metadata
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice_row = dict(cursor.fetchone())

    # 2. Fetch Company (Seller)
    cursor.execute("SELECT * FROM company_profile WHERE id = ?", (invoice_row['company_id'],))
    company_row = dict(cursor.fetchone())

    # 3. Fetch Buyer (Client)
    cursor.execute("SELECT * FROM clients WHERE id = ?", (invoice_row['client_id'],))
    buyer_row = dict(cursor.fetchone())

    # 4. Fetch Consignee (Shipping)
    consignee_row = {}
    if invoice_row['shipping_id']:
        cursor.execute("SELECT * FROM shipping_addresses WHERE id = ?", (invoice_row['shipping_id'],))
        row = cursor.fetchone()
        if row: consignee_row = dict(row)

    # 5. Fetch Items
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    item_rows = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Fix buyer address keys: clients table uses billing_address_line_1/2
    # but the gst_invoice.html template expects address_line_1/2
    buyer_row['address_line_1'] = buyer_row.get('billing_address_line_1') or buyer_row.get('address_line_1', '')
    buyer_row['address_line_2'] = buyer_row.get('billing_address_line_2') or buyer_row.get('address_line_2', '')

    # If no separate shipping/consignee address, default to buyer (bill to = ship to)
    if not consignee_row:
        consignee_row = dict(buyer_row)

    # Fix company bank field: template uses {{ company.bank_branch_ifsc }}
    # but DB stores bank_branch and bank_ifsc as separate columns
    company_row['bank_branch_ifsc'] = ' / '.join(filter(None, [
        company_row.get('bank_branch', '') or '',
        company_row.get('bank_ifsc', '') or ''
    ]))

    return {
        "company": company_row,
        "invoice": invoice_row,
        "buyer": buyer_row,
        "consignee": consignee_row,
        "items": item_rows
    }

async def generate_pdf(html_path, pdf_path):
    """Uses playwright to generate PDF from HTML."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f'file:///{os.path.abspath(html_path)}')
        await page.emulate_media(media="print")
        await page.pdf(path=pdf_path, format='A4', print_background=True, margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
        await browser.close()

if __name__ == "__main__":
    db_file = "invoices.db"
    
    # If DB doesn't exist, we can't fetch. In real app, user would run setup first.
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found. Please run setup_sqlite.py first.")
    else:
        print(f"Fetching data from {db_file}...")
        invoice_data = fetch_invoice_data(db_file)
        
        if invoice_data:
            renderer = InvoiceRenderer()
            html_out = renderer.render(invoice_data, 'rendered_invoice.html')
            print(f"HTML rendered to {html_out}")
            
            asyncio.run(generate_pdf(html_out, 'GST_Invoice_Refined.pdf'))
            print("PDF generated successfully from database data!")
        else:
            print("No invoice data found in the database.")
