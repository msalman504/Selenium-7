import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# ✅ Define the accepted appointment button color
ACCEPTED_COLOR = "rgb(10, 48, 143)"  # This is the RGB equivalent of #0a308f

def read_credentials(file_path="credentials.txt"):
    """
    Reads credentials from a file. Expected format:
    URL
    Username
    Password
    """
    credentials = []
    with open(file_path, "r") as f:
        lines = f.readlines()
        # Process in chunks of 3 lines
        for i in range(0, len(lines), 3):
            if i + 2 < len(lines):
                url = lines[i].strip()
                username = lines[i+1].strip()
                password = lines[i+2].strip()
                credentials.append({"url": url, "username": username, "password": password})
            else:
                print(f"❌ Incomplete credentials at lines {i}-{i+2}. Skipping.")
    return credentials

def setup_driver():
    """
    Initializes the Selenium WebDriver in non-headless mode.
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent bot detection
    service = ChromeService()  # Initialize the ChromeDriver service
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login(driver, url, username, password):
    """
    Logs into the TLSContact website using Selenium.
    """
    print(f"🔵 Navigating to: {url}")
    driver.get(url)

    try:
        wait = WebDriverWait(driver, 10)
        username_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_input = driver.find_element(By.ID, "password")

        username_input.clear()
        username_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)

        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        time.sleep(5)  # Wait for login to process
        print("✅ Logged in successfully.")
        return True
    except (NoSuchElementException, TimeoutException) as e:
        print("❌ Error during login:", e)
        return False

def choose_and_confirm_appointment(driver, username):
    """
    Searches for available appointment buttons that meet the required time (10:00 - 14:00)
    and background color (`rgb(10, 48, 143)`). Clicks the button and confirms the appointment.
    """
    try:
        available_buttons = driver.find_elements(By.CSS_SELECTOR, "button.tls-time-unit.-available")
        print(f"🔍 {username}: Found {len(available_buttons)} available appointment button(s).")

        for btn in available_buttons:
            # Extract appointment time from button text
            time_text = btn.text.strip()
            try:
                hour, minute = map(int, time_text.split(":"))
            except ValueError:
                print(f"⏩ {username}: Skipping button with unexpected time format: {time_text}")
                continue  # Skip if time format is incorrect

            # Extract button color using JavaScript
            color = driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", btn)
            print(f"🎨 {username}: Checking button - Time: {time_text}, Color: {color}")

            # Only proceed if time is within range AND color matches
            if 10 <= hour < 14 and color == ACCEPTED_COLOR:
                print(f"✅ {username}: Suitable appointment found at {time_text} with color {color}. Clicking the button.")

                # Scroll into view before clicking
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.5)

                try:
                    btn.click()
                except Exception:
                    print("⚠️ Normal click failed. Trying JavaScript click.")
                    driver.execute_script("arguments[0].click();", btn)

                # Wait for the confirmation popup and click the confirm button
                return confirm_appointment(driver, time_text, username)

        return {
            "status": "No Matching Appointments",
            "message": f"❌ {username}: No appointments with the preferred color found."
        }

    except Exception as e:
        return {
            "status": "Error",
            "message": str(e)
        }

def confirm_appointment(driver, time_text, username):
    """
    Waits for the confirmation popup and clicks the 'Confirm' button.
    """
    try:
        # Wait for the confirmation popup to appear and the button to be clickable
        wait = WebDriverWait(driver, 10)
        confirm_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tls-value='confirm']"))
        )

        # Scroll to the confirmation button to ensure it's in view
        driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
        time.sleep(1)  # Wait a bit for the button to be in view

        # Try clicking the confirmation button
        try:
            confirm_button.click()
            print(f"🎉 {username}: Appointment confirmed at {time_text}!")
        except Exception as click_error:
            print(f"⚠️ {username}: Normal click failed for confirmation. Using JavaScript click. Error: {click_error}")
            driver.execute_script("arguments[0].click();", confirm_button)

        # Now wait for and click the "Proceed" button on the next page
        proceed_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.tls-button-primary.-uppercase"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button)
        time.sleep(1)  # Ensure the button is in view
        proceed_button.click()
        print(f"🎉 {username}: Proceeded to the next step.")

        return {
            "status": "Success",
            "message": f"✅ {username}: Appointment booked at {time_text} and proceeded.",
            "time": time_text
        }

    except TimeoutException:
        print(f"❌ {username}: Confirmation popup did not appear in time.")
        return {
            "status": "Error",
            "message": f"❌ {username}: Confirmation button did not appear in time."
        }
    except Exception as e:
        print(f"❌ {username}: Error while confirming appointment: {e}")
        return {
            "status": "Error",
            "message": f"❌ {username}: Error while confirming appointment: {str(e)}"
        }

def run_for_user(user):
    """
    Runs the entire appointment booking flow for a specific user.
    """
    username = user["username"]
    password = user["password"]
    url = user["url"]
    driver = setup_driver()

    try:
        while True:
            print(f"\n--- 🔄 New Check for {username} ---")
            if login(driver, url, username, password):
                result_data = choose_and_confirm_appointment(driver, username)
                print(result_data)
                if result_data["status"] == "Success":
                    print(f"🎯 {username}: Appointment confirmed! Exiting...")
                    break  # Stop checking after a successful booking
            else:
                print(f"❌ {username}: Login failed. Retrying in 2 minutes...")

            print(f"⏳ {username}: Waiting for 2 minutes before the next check...")
            time.sleep(60)
            driver.refresh()

    except KeyboardInterrupt:
        print(f"❌ {username}: Script interrupted by user.")
    finally:
        driver.quit()
        print(f"🚪 {username}: Driver closed.")

def main():
    """
    Main function to run multiple browser instances for multiple users.
    """
    credentials = read_credentials("credentials.txt")
    threads = []

    for user in credentials:
        thread = threading.Thread(target=run_for_user, args=(user,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
