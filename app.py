from flask import Flask, jsonify, request
from scraper.browser_automation import get_result_pdf_link
from scraper.pdf_handler import download_pdf, extract_text_from_pdf
from scraper.result_parser import parse_result_text
import os
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

DATA_DIR = "data"
OUTPUT_DIR = "output"
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_path_for_roll(roll, session, semester):
    # include session and semester in cache filename to distinguish
    filename = f"{roll}_{session}_{semester}.json"
    return os.path.join(CACHE_DIR, filename)

def save_to_cache(roll, session, semester, data):
    with open(cache_path_for_roll(roll, session, semester), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_from_cache(roll, session, semester):
    path = cache_path_for_roll(roll, session, semester)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

@app.route('/run_batch', methods=['GET'])
def run_batch():
    results = []

    session = request.args.get("session", "116")
    semester = request.args.get("semester", "6")

    start_roll = request.args.get("start_roll", default=22115001, type=int)
    end_roll = request.args.get("end_roll", default=22115002, type=int)

    for roll in range(start_roll, end_roll + 1):
        roll_str = str(roll)

        cached_result = load_from_cache(roll_str, session, semester)
        if cached_result:
            print(f"Using cached result for roll {roll_str}")
            results.append(cached_result)
            continue

        try:
            print(f"Fetching PDF for roll: {roll_str}, session: {session}, semester: {semester}")
            result = get_result_pdf_link(roll_str, session, semester)
            
            if "pdf_url" not in result:
                print(f"❌ Error fetching PDF URL for roll {roll_str}: {result.get('error', 'No URL found')}")
                continue

            pdf_url = result["pdf_url"]
            pdf_filename = os.path.join(DATA_DIR, f"result_{roll_str}.pdf")
            
            print(f"Downloading PDF from URL: {pdf_url}")
            download_pdf(pdf_url, pdf_filename)
            print(f"Downloaded PDF for {roll_str}")

            text = extract_text_from_pdf(pdf_filename)
            print(f"Extracted text for {roll_str}")

            parsed_data = parse_result_text(text)
            os.remove(pdf_filename)
            print(f"Deleted PDF for {roll_str}")

            parsed_data["roll_number"] = parsed_data.get("roll_number") or roll_str

            result_data = {
                "roll": roll_str,
                "pdf_url": pdf_url,
                "session": session,
                "semester": semester,
                **parsed_data
            }
            save_to_cache(roll_str, session, semester, result_data)
            results.append(result_data)

        except Exception as e:
            print(f"❌ Error processing roll {roll_str}: {e}")

    output_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Finished processing batch. Results saved to: {output_path}")

    return jsonify({
        "message": "Batch processing complete",
        "total_results": len(results),
        "output_file": output_path
    })

@app.route('/api/result', methods=['GET'])
def get_single_result():
    roll = request.args.get("roll")
    session = request.args.get("session", "116")
    semester = request.args.get("semester", "6")

    if not roll:
        return jsonify({"error": "Missing 'roll' query parameter"}), 400

    cached_result = load_from_cache(roll, session, semester)
    if cached_result:
        print(f"Using cached result for roll {roll}")
        return jsonify(cached_result)

    try:
        print(f"Fetching PDF for single roll: {roll}, session: {session}, semester: {semester}")
        result = get_result_pdf_link(roll, session, semester)

        if "pdf_url" not in result:
            return jsonify({"error": result.get("error", "No PDF URL found")}), 400

        pdf_url = result["pdf_url"]
        pdf_filename = os.path.join(DATA_DIR, f"result_{roll}.pdf")
        
        print(f"Downloading PDF from URL: {pdf_url}")
        download_pdf(pdf_url, pdf_filename)
        print(f"Downloaded PDF for {roll}")

        text = extract_text_from_pdf(pdf_filename)
        print(f"Extracted text for {roll}")

        parsed_data = parse_result_text(text)
        os.remove(pdf_filename)
        print(f"Deleted PDF for {roll}")

        parsed_data["roll_number"] = parsed_data.get("roll_number") or roll

        result_data = {
            "roll": roll,
            "pdf_url": pdf_url,
            "session": session,
            "semester": semester,
            **parsed_data
        }
        save_to_cache(roll, session, semester, result_data)

        return jsonify(result_data)

    except Exception as e:
        print(f"❌ Error processing roll {roll}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
