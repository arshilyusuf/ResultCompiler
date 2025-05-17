import re

def parse_result_text(text):
    data = {}

    # 1. Extract name cleanly
    # Example regex: match line starting with "Name" or something similar
    # Or use a known pattern from PDF text structure
    # Here is an example of removing extra unwanted text after the name:
    name_match = re.search(r'Name\s*:\s*([A-Za-z\s]+)', text)
    if name_match:
        data["name"] = name_match.group(1).strip()
    else:
        # fallback: try some heuristic or assign None
        data["name"] = None

    # 2. Extract father's name and enrollment number separately
    # Suppose text has a line like:
    # "Father's Name : SUSIL KUMAR SINGH Enrollment No : 220518"
    father_enroll_match = re.search(r"Father's Name\s*:\s*([A-Za-z\s]+)\s+Enrollment No\s*:\s*(\d+)", text)
    if father_enroll_match:
        data["father_name"] = father_enroll_match.group(1).strip()
        data["enrollment_number"] = father_enroll_match.group(2).strip()
    else:
        # fallback or partial match
        # maybe father's name only, no enrollment number
        father_match = re.search(r"Father's Name\s*:\s*([A-Za-z\s]+)", text)
        data["father_name"] = father_match.group(1).strip() if father_match else None
        data["enrollment_number"] = None

    # 3. Extract result subjects with their fields
    # Assuming PDF text has subjects listed in some tabular or patterned format like:
    # SubjectCode SubjectName Grade GradePoint Credits
    # This will depend heavily on your PDF text format, but a generic approach:

    result = {}
    # Example regex for lines with subject info (very generic):
    # Adjust pattern to match your exact subject line format
    subject_pattern = re.compile(r'([A-Z0-9]+)\s+([A-Za-z\s&]+)\s+([A-FOP])\s+([\d.]+)\s+(\d+)')
    for match in subject_pattern.finditer(text):
        subject_code = match.group(1).strip()
        subject_name = match.group(2).strip()
        grade = match.group(3).strip()
        grade_point = float(match.group(4).strip())
        credits = int(match.group(5).strip())
        # use subject_name or subject_code as key; e.g. subject_name
        result[subject_name] = {
            "grade": grade,
            "gradepoint": grade_point,
            "credits": credits
        }
    data["result"] = result

    # 4. Extract result_pf (pass/fail)
    pf_match = re.search(r'Result\s*:\s*(PASS|FAIL)', text, re.IGNORECASE)
    data["result_pf"] = pf_match.group(1).upper() if pf_match else None

    # 5. Extract SPI and CPI (may have decimals)
    spi_match = re.search(r'SPI\s*:\s*([\d.]+)', text)
    data["SPI"] = float(spi_match.group(1)) if spi_match else None

    cpi_match = re.search(r'CPI\s*:\s*([\d.]+)', text)
    data["CPI"] = float(cpi_match.group(1)) if cpi_match else None

    # 6. Extract total credits
    credits_match = re.search(r'Total Credits\s*:\s*(\d+)', text)
    data["total_credits"] = int(credits_match.group(1)) if credits_match else None

    return data
