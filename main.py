from scraper.browser_automation import get_result_pdf_link
from scraper.pdf_handler import download_pdf, extract_text_from_pdf
from scraper.result_parser import parse_result_text  # <-- import parser
import os
import json

DATA_DIR = "data"
OUTPUT_DIR = "output"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    results = []

    for roll in range(22115001, 22115003):
        roll_str = str(roll)
        try:
            print(f"Fetching PDF for roll: {roll_str}")
            pdf_url = get_result_pdf_link(roll_str, "116", "6")
            pdf_filename = os.path.join(DATA_DIR, f"result_{roll_str}.pdf")
            
            download_pdf(pdf_url, pdf_filename)
            print(f"Downloaded PDF for {roll_str}")

            text = extract_text_from_pdf(pdf_filename)
            print(f"Extracted text for {roll_str}")
            print(f"Raw text for roll {roll_str}:\n{text[:2000]}")  # print first 2000 chars for debugging

            parsed_data = parse_result_text(text)  # <-- parse extracted text
            os.remove(pdf_filename)
            print(f"Deleted PDF for {roll_str}")
            # Ensure roll number is included (fallback to roll_str if missing)
            parsed_data["roll_number"] = parsed_data.get("roll_number") or roll_str

            results.append({
                "roll": roll_str,
                "pdf_url": pdf_url,
                **parsed_data  # <-- merge parsed data here
            })

        except Exception as e:
            print(f"❌ Error processing roll {roll_str}: {e}")

    print(f"\nTotal results collected: {len(results)}")  # <-- debug print

    # Save results
    output_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Finished processing. Results saved to: {output_path}")

if __name__ == "__main__":
    main()
