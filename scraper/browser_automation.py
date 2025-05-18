from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service
import time
import re
import tempfile
import shutil
import uuid
import os

BASE_URL = "https://mis.nitrr.ac.in/iitmsoBF2zO1QWoLeV7wV7kw7kcHJeahVjzN4t6MFMeyhUykpKfBA9V+F0/3m6SMOr7hf?enc=2vjcaEnhmvfs4iwSJr18eQaN1iwTCkDZLg4FpnIV12/vTB0HoHDs8kZdmyK5DB9t"

MAX_RETRIES = 3

def safe_find(driver, by, value, retries=MAX_RETRIES):
    for _ in range(retries):
        try:
            return driver.find_element(by, value)
        except StaleElementReferenceException:
            time.sleep(1)
    raise StaleElementReferenceException(f"Failed to find stable element: {value}")

def safe_click(driver, element):
    try:
        ActionChains(driver).move_to_element(element).click().perform()
    except:
        element.click()

def get_result_pdf_link(roll_no, session_value, semester_value):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    unique_id = uuid.uuid4().hex
    temp_user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_{unique_id}")
    os.makedirs(temp_user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")
    
    # Use ChromeService for better resource management
    service = Service()

    try:
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 30)  # Increased from 15 to 30 seconds
        
        driver.get(BASE_URL)

        roll_input = wait.until(EC.presence_of_element_located((By.ID, "txtRegno")))
        roll_input.clear()
        roll_input.send_keys(roll_no)

        show_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnimgShow")))
        show_btn.click()

        time.sleep(1)

        # Handle alert (invalid roll)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return {"error": f"❌ Alert from site: {alert_text}"}
        except:
            pass

        # Wait and select session
        wait.until(EC.presence_of_element_located((By.ID, "ddlSession")))
        session_elem = safe_find(driver, By.ID, "ddlSession")
        Select(session_elem).select_by_value(session_value)

        # Wait for semester dropdown to update
        initial_semester_elem = safe_find(driver, By.ID, "ddlSemester")
        initial_options = len(Select(initial_semester_elem).options)

        def semester_updated(driver):
            try:
                updated_elem = driver.find_element(By.ID, "ddlSemester")
                return len(Select(updated_elem).options) != initial_options and len(Select(updated_elem).options) > 1
            except StaleElementReferenceException:
                return False

        wait.until(semester_updated)

        # Re-fetch and select semester
        semester_elem = safe_find(driver, By.ID, "ddlSemester")
        Select(semester_elem).select_by_value(semester_value)

        # Wait for CBCS button
        wait.until(EC.presence_of_element_located((By.ID, "btnCBCSTabulation")))

        # Scroll into view and ensure stable reference
        cbc_btn = None
        for _ in range(MAX_RETRIES):
            try:
                cbc_btn = safe_find(driver, By.ID, "btnCBCSTabulation")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cbc_btn)
                time.sleep(1)
                break
            except StaleElementReferenceException:
                time.sleep(1)

        if cbc_btn is None:
            return {"error": "❌ Could not locate CBCS button"}

        # Try getting PDF URL directly
        for _ in range(MAX_RETRIES):
            try:
                cbc_btn = safe_find(driver, By.ID, "btnCBCSTabulation")
                href = cbc_btn.get_attribute("href")
                if href:
                    return {"pdf_url": href}

                onclick = cbc_btn.get_attribute("onclick")
                if onclick:
                    match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick)
                    if match:
                        return {"pdf_url": match.group(1)}
                break
            except StaleElementReferenceException:
                time.sleep(1)

        # Fallback: simulate click and switch tab
        for _ in range(MAX_RETRIES):
            try:
                cbc_btn = safe_find(driver, By.ID, "btnCBCSTabulation")
                safe_click(driver, cbc_btn)
                break
            except StaleElementReferenceException:
                time.sleep(1)

        wait.until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[-1])
        pdf_url = driver.current_url
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return {"pdf_url": pdf_url}

    except TimeoutException:
        return {"error": "⏳ Timeout while loading page or element"}
    except Exception as e:
        return {"error": f"⚠️ Selenium error: {str(e)}"}
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass
        try:
            shutil.rmtree(temp_user_data_dir, ignore_errors=True)
        except:
            pass
