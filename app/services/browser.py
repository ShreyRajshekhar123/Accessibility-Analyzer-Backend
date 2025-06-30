# app/services/browser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

import os

def get_webdriver(browser_type: str = "chrome"):
    """
    Initializes and returns a headless Selenium WebDriver.
    Supports 'chrome' and 'firefox'.
    """
    if browser_type.lower() == "chrome":
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--log-level=3")

        # Use pre-installed Chromium on Render
        options.binary_location = "/usr/bin/chromium"

        try:
            # Use pre-installed chromedriver path directly
            service = ChromeService(executable_path="/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            print(f"[Chrome] Error initializing WebDriver: {e}")
            raise

    elif browser_type.lower() == "firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Firefox binary path (if installed on Render, though Chromium is preferred)
        options.binary_location = "/usr/bin/firefox"

        try:
            service = FirefoxService(executable_path="/usr/bin/geckodriver")
            driver = webdriver.Firefox(service=service, options=options)
            return driver
        except Exception as e:
            print(f"[Firefox] Error initializing WebDriver: {e}")
            raise

    else:
        raise ValueError("Unsupported browser type. Choose 'chrome' or 'firefox'.")


# Optional: CLI test runner
if __name__ == "__main__":
    print("Testing Chrome headless browser...")
    try:
        driver = get_webdriver("chrome")
        driver.get("http://www.example.com")
        print(f"Chrome Title: {driver.title}")
        driver.quit()
        print("Chrome test successful.")
    except Exception as e:
        print(f"Chrome test failed: {e}")

    print("\nTesting Firefox headless browser...")
    try:
        driver = get_webdriver("firefox")
        driver.get("http://www.example.com")
        print(f"Firefox Title: {driver.title}")
        driver.quit()
        print("Firefox test successful.")
    except Exception as e:
        print(f"Firefox test failed: {e}")
