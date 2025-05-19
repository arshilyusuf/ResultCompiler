import logging
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

ENABLE_LOGGING = True

logging.basicConfig(
    level=logging.INFO if ENABLE_LOGGING else logging.CRITICAL,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
BASE_URL = "https://mis.nitrr.ac.in/iitmsoBF2zO1QWoLeV7wV7kw7kcHJeahVjzN4t6MFMeyhUykpKfBA9V+F0/3m6SMOr7hf?enc=2vjcaEnhmvfs4iwSJr18eQaN1iwTCkDZLg4FpnIV12/vTB0HoHDs8kZdmyK5DB9t"
MAX_RETRIES = 3

def safe_find(driver, by, value, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            element = driver.find_element(by, value)
            logging.debug(f"Element found: {value}")
            return element
        except StaleElementReferenceException:
            logging.warning(f"StaleElementReferenceException on {value}, retrying... ({attempt + 1})")
            time.sleep(1)
    raise StaleElementReferenceException(f"Failed to find stable element: {value}")

def safe_click(driver, element):
    try:
        ActionChains(driver).move_to_element(element).click().perform()
        logging.debug("Clicked using ActionChains.")
    except Exception as e:
        logging.warning(f"ActionChains click failed: {e}. Using element.click()")
        element.click()

def get_result_pdf_link(roll_no, session_value, semester_value):
    logging.info("Starting PDF retrieval process...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    unique_id = uuid.uuid4().hex
    temp_user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_{unique_id}")
    os.makedirs(temp_user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")

    service = Service()

    try:
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 60)  # Increased timeout to 60 seconds

        logging.info("Navigating to MIS portal...")
        driver.get(BASE_URL)

        roll_input = wait.until(EC.presence_of_element_located((By.ID, "txtRegno")))
        roll_input.clear()
        roll_input.send_keys(roll_no)
        logging.info(f"Entered roll number: {roll_no}")

        show_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnimgShow")))
        show_btn.click()
        logging.info("Clicked 'Show' button.")

        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            logging.warning(f"Alert detected: {alert_text}")
            return {"error": f"❌ Alert from site: {alert_text}"}
        except:
            logging.debug("No alert found.")

        session_elem = wait.until(EC.presence_of_element_located((By.ID, "ddlSession")))
        current_session = Select(session_elem).first_selected_option.get_attribute("value")

        if current_session != session_value:
            Select(session_elem).select_by_value(session_value)
            logging.info(f"Selected session: {session_value}")

            # Wait for semester dropdown to update
            initial_semester_elem = safe_find(driver, By.ID, "ddlSemester")
            initial_options = len(Select(initial_semester_elem).options)
            logging.debug(f"Initial semester options count: {initial_options}")

            def semester_updated(driver):
                try:
                    updated_elem = driver.find_element(By.ID, "ddlSemester")
                    return len(Select(updated_elem).options) != initial_options and len(Select(updated_elem).options) > 1
                except StaleElementReferenceException:
                    return False

            wait.until(semester_updated)
            time.sleep(0.5)  # slight pause to ensure stability
        else:
            logging.info(f"Session already selected as: {current_session}, skipping session selection.")

        semester_elem = safe_find(driver, By.ID, "ddlSemester")
        wait.until(lambda d: semester_elem.is_enabled())
        Select(semester_elem).select_by_value(semester_value)
        logging.info(f"Selected semester: {semester_value}")

        for attempt in range(MAX_RETRIES):
            try:
                wait.until(EC.presence_of_element_located((By.ID, "btnCBCSTabulation")))
                logging.debug("CBCS button is present.")
                break
            except TimeoutException:
                if attempt == MAX_RETRIES - 1:
                    logging.error("CBCS button not found after retries.")
                    return {"error": "⏳ Timeout waiting for CBCS button"}
                logging.warning("Retrying wait for CBCS button...")
                time.sleep(3)  # Increased sleep before retry

        cbc_btn = None
        for _ in range(MAX_RETRIES):
            try:
                cbc_btn = safe_find(driver, By.ID, "btnCBCSTabulation")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cbc_btn)
                wait.until(EC.element_to_be_clickable((By.ID, "btnCBCSTabulation")))
                logging.info("CBCS button located and ready.")
                break
            except StaleElementReferenceException:
                logging.warning("Stale CBCS button reference, retrying...")
                time.sleep(1)

        if not cbc_btn:
            return {"error": "❌ Could not locate CBCS button"}

        for _ in range(MAX_RETRIES):
            try:
                cbc_btn = safe_find(driver, By.ID, "btnCBCSTabulation")
                href = cbc_btn.get_attribute("href")
                if href:
                    logging.info(f"Found direct PDF link: {href}")
                    return {"pdf_url": href}

                onclick = cbc_btn.get_attribute("onclick")
                if onclick:
                    match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick)
                    if match:
                        logging.info("Extracted PDF URL from onclick.")
                        return {"pdf_url": match.group(1)}
                time.sleep(1)
            except StaleElementReferenceException:
                logging.warning("Retrying PDF URL extraction due to stale reference.")
                time.sleep(1)

        logging.info("Falling back to click and tab switch method...")
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
        logging.info(f"PDF URL after clicking and switching tab: {pdf_url}")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return {"pdf_url": pdf_url}

    except TimeoutException:
        logging.error("Timeout while waiting for element.")
        return {"error": "⏳ Timeout while loading page or element"}
    except Exception as e:
        logging.exception("Unhandled Selenium exception occurred.")
        return {"error": f"⚠️ Selenium error: {str(e)}"}
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
                logging.debug("Driver quit successfully.")
        except Exception as e:
            logging.warning(f"Failed to quit driver: {e}")
        try:
            shutil.rmtree(temp_user_data_dir, ignore_errors=True)
            logging.debug("Temporary user data directory cleaned.")
        except Exception as e:
            logging.warning(f"Failed to remove temp user dir: {e}")
