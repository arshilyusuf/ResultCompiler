from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import tempfile
import os
import shutil

BASE_URL = "https://mis.nitrr.ac.in/iitmsoBF2zO1QWoLeV7wV7kw7kcHJeahVjzN4t6MFMeyhUykpKfBA9V+F0/3m6SMOr7hf?enc=2vjcaEnhmvfs4iwSJr18eQaN1iwTCkDZLg4FpnIV12/vTB0HoHDs8kZdmyK5DB9t"

def get_result_pdf_link(roll_no, session_value, semester_value):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    temp_user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(BASE_URL)

        # Enter roll number
        roll_input = wait.until(EC.presence_of_element_located((By.ID, "txtRegno")))
        roll_input.clear()
        roll_input.send_keys(roll_no)

        # Click show button
        show_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnimgShow")))
        show_btn.click()
        time.sleep(1)

        # Handle alert if it appears
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return {"error": f"❌ Alert from site: {alert_text}"}
        except:
            pass

        # Select session
        wait.until(EC.presence_of_element_located((By.ID, "ddlSession")))
        session_select = Select(driver.find_element(By.ID, "ddlSession"))
        session_select.select_by_value(session_value)

        # Wait for semester dropdown to populate
        for _ in range(10):
            semester_select = Select(driver.find_element(By.ID, "ddlSemester"))
            options_list = [opt.get_attribute("value") for opt in semester_select.options]
            if len(options_list) > 1:
                break
            time.sleep(1)
        else:
            return {"error": f"⚠️ Semester dropdown did not populate for roll {roll_no}"}

        if semester_value not in options_list:
            return {"error": f"⚠️ Semester {semester_value} not available for roll {roll_no}"}

        semester_select.select_by_value(semester_value)

        # Wait for button
        cbc_btn = wait.until(EC.presence_of_element_located((By.ID, "btnCBCSTabulation")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cbc_btn)
        time.sleep(1)

        # Try direct href
        pdf_url = cbc_btn.get_attribute("href")
        if pdf_url:
            return {"pdf_url": pdf_url}

        # Try onclick attribute
        onclick_attr = cbc_btn.get_attribute("onclick")
        if onclick_attr:
            match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick_attr)
            if match:
                return {"pdf_url": match.group(1)}

        # Try clicking to open new tab
        try:
            ActionChains(driver).move_to_element(cbc_btn).click().perform()
        except:
            cbc_btn.click()

        wait.until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[-1])
        pdf_url = driver.current_url

        # Cleanup and return
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return {"pdf_url": pdf_url}

    except Exception as e:
        return {"error": f"⚠️ Selenium error: {str(e)}"}

    finally:
        driver.quit()
        shutil.rmtree(temp_user_data_dir, ignore_errors=True)
