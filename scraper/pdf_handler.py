import requests
import pdfplumber
import logging

ENABLE_LOGGING = True

logging.basicConfig(
    level=logging.INFO if ENABLE_LOGGING else logging.CRITICAL,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
def download_pdf(url, filename):
    logging.info(f"Attempting to download PDF from: {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)  # SSL verify disabled
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        logging.info(f"PDF successfully downloaded and saved as: {filename}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise RuntimeError(f"Failed to download PDF from {url}: {e}")
    except Exception as e:
        logging.exception("Unexpected error while downloading PDF.")
        raise RuntimeError(f"Failed to download PDF from {url}: {e}")

def extract_text_from_pdf(filename):
    logging.info(f"Starting text extraction from PDF: {filename}")
    try:
        full_text = ""
        with pdfplumber.open(filename) as pdf:
            logging.debug(f"PDF opened successfully. Total pages: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                logging.debug(f"Extracted text from page {i + 1}")
                if page_text:
                    full_text += page_text + "\n"
        logging.info("Text extraction completed successfully.")
        return full_text.strip()
    except Exception as e:
        logging.exception("Failed during PDF text extraction.")
        raise RuntimeError(f"Failed to extract text from {filename}: {e}")
