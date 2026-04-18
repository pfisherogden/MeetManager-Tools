import pdfplumber

def check_entries(file_path):
    print(f"--- Checking Entries: {file_path} ---")
    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            for i in range(min(3, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                lines = text.split('\n') if text else []
                # Find lines that look like entries, not headers
                data_lines = [l for l in lines if not l.startswith('TVSL') and not l.startswith('Entries') and not l.startswith('Team Entries') and not l.startswith('Ev#')]
                print(f"Page {i} data sample: {data_lines[:5]}")
    except Exception as e:
        print(f"Error: {e}")

def check_results(file_path):
    print(f"--- Checking Results: {file_path} ---")
    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            for i in range(min(2, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                lines = text.split('\n') if text else []
                data_lines = [l for l in lines if 'Pl ' not in l and not l.startswith('Event') and not l.startswith('TVSL') and not l.startswith('Meet')]
                print(f"Page {i} data sample: {data_lines[:5]}")
    except Exception as e:
        print(f"Error: {e}")

def check_timer_sheets(file_path):
    print(f"--- Checking Timer Sheets: {file_path} ---")
    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            # Check for page breaks per lane (1/3 and 2/4 vertical alignment)
            for i in range(min(4, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                lines = text.split('\n') if text else []
                lane_headers = [l for l in lines if 'Lane' in l and 'Page' in l]
                print(f"Page {i} lane headers: {lane_headers}")
                
                # Check layout
                # Find the bounding boxes of words to see if 1/3 and 2/4 alignment is preserved.
                words = pdf.pages[i].extract_words()
                print(f"Page {i} word sample count: {len(words)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    base = '/Users/pfo/Developer/MeetManager-Tools/'
    check_entries(base + 'comp_weasy_entries.pdf')
    check_entries(base + 'comp_playwright_entries.pdf')
    check_results(base + 'comp_weasy_results.pdf')
    check_results(base + 'comp_playwright_results.pdf')
    check_timer_sheets(base + 'comp_playwright_timer_sheets.pdf')
