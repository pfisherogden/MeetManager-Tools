import sys
import pdfplumber

def dump_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        return text

if __name__ == "__main__":
    text = dump_pdf("/Users/pfo/Developer/tmp/girls_meet_program_for_posting.pdf")
    lines = text.split('\n')
    for i, line in enumerate(lines[:100]):
        print(line)
