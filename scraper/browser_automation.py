from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import tempfile


BASE_URL = "https://mis.nitrr.ac.in/iitmsoBF2zO1QWoLeV7wV7kw7kcHJeahVjzN4t6MFMeyhUykpKfBA9V+F0/3m6SMOr7hf?enc=2vjcaEnhmvfs4iwSJr18eQaN1iwTCkDZLg4FpnIV12/vTB0HoHDs8kZdmyK5DB9t"

def get_result_pdf_link(roll_no, session_value, semester_value):
    options = Options()
    options.add_argument("--headless")  # recommended for headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    temp_profile = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_profile}")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(BASE_URL)

        # Enter roll number
        roll_input = wait.until(EC.presence_of_element_located((By.ID, "txtRegno")))
        roll_input.clear()
        roll_input.send_keys(roll_no)

        # Click "Show" button
        show_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnimgShow")))
        show_btn.click()

        # Wait for session dropdown and select session
        wait.until(EC.presence_of_element_located((By.ID, "ddlSession")))
        session_select = Select(driver.find_element(By.ID, "ddlSession"))
        session_select.select_by_value(session_value)

        # Wait for semester dropdown options to reload
        wait.until(lambda d: len(Select(d.find_element(By.ID, "ddlSemester")).options) > 1)

        # Select semester
        semester_select = Select(driver.find_element(By.ID, "ddlSemester"))
        semester_select.select_by_value(semester_value)

        # Scroll CBCS button into view
        cbc_btn = wait.until(EC.presence_of_element_located((By.ID, "btnCBCSTabulation")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cbc_btn)
        time.sleep(1)

        # Try to get PDF URL directly from href attribute
        pdf_url = cbc_btn.get_attribute("href")
        if pdf_url:
            return pdf_url

        # If href not found, try extracting URL from onclick attribute
        onclick_attr = cbc_btn.get_attribute("onclick")
        if onclick_attr:
            match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick_attr)
            if match:
                pdf_url = match.group(1)
                return pdf_url

        # Fallback: click the button and switch tabs (headless, invisible)
        try:
            ActionChains(driver).move_to_element(cbc_btn).click().perform()
        except Exception:
            cbc_btn.click()

        wait.until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[-1])
        pdf_url = driver.current_url

        # Close PDF tab and switch back
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return pdf_url

    finally:
        driver.quit()
