import pdfplumber
import sys

def extract_text(path, pages):
    with pdfplumber.open(path) as pdf:
        for p in pages:
            if p <= len(pdf.pages):
                page = pdf.pages[p-1]
                print(f"--- Page {p} ---")
                print(page.extract_text())

if __name__ == "__main__":
    extract_text(sys.argv[1], [7, 8])
