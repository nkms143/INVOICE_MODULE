import sys
import argparse
from playwright.sync_api import sync_playwright

def generate_pdf(html_input_path: str, pdf_output_path: str):
    """
    Converts an elegant HTML invoice into a highly polished PDF.
    This script is intended to be called by Layer 2 Orchestrators.
    """
    with sync_playwright() as p:
        # Launch headless Chromium
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Load the local HTML file (must be absolute path or relative to script execution dir)
        import os
        abs_path = os.path.abspath(html_input_path)
        page.goto(f"file:///{abs_path}", wait_until="networkidle")
        
        # Generate the PDF with typical professional print settings
        page.pdf(
            path=pdf_output_path,
            format="A4",
            print_background=True,    # Extremely important for CSS backgrounds and colors
            margin={
                "top": "1cm",
                "right": "1cm",
                "bottom": "1cm",
                "left": "1cm"
            }
        )
        
        browser.close()
        print(f"✅ Successfully generated elegant invoice PDF at: {pdf_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PDF from HTML.")
    parser.add_argument("html_input", help="Path to the source HTML file (.tmp/invoice.html)")
    parser.add_argument("pdf_output", help="Path to save the generated PDF (.tmp/invoice.pdf)")
    
    args = parser.parse_args()
    
    # Try block for self-annealing debugging if something breaks in orchestrator layer
    try:
        generate_pdf(args.html_input, args.pdf_output)
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}", file=sys.stderr)
        print("Note for Orchestrator: Please ensure you have run 'pip install playwright' and 'playwright install chromium'", file=sys.stderr)
        sys.exit(1)
