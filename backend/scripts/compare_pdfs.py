import pdfplumber
import sys

def analyze_pdf(path):
    print(f"\n--- Analyzing {path} ---")
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"Page {i+1}:")
            text = page.extract_text()
            print(text[:1000] if text else "No text found")
            if i >= 1: break # Only first 2 pages

if __name__ == "__main__":
    analyze_pdf(sys.argv[1])
    analyze_pdf(sys.argv[2])
