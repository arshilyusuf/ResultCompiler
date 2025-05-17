import requests
import pdfplumber

def download_pdf(url, filename):
    try:
        response = requests.get(url, timeout=10, verify=False)  # <== SSL verify disabled
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise RuntimeError(f"Failed to download PDF from {url}: {e}")
def extract_text_from_pdf(filename):
    try:
        full_text = ""
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        return full_text.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {filename}: {e}")
