# app/services/browser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService # Import Service for Chrome
from selenium.webdriver.firefox.service import Service as FirefoxService # Import Service for Firefox

# UNCOMMENT AND USE THESE LINES
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import os

def get_webdriver(browser_type: str = "chrome"):
    """
    Initializes and returns a headless Selenium WebDriver.
    Supports 'chrome' and 'firefox'.
    """
    if browser_type.lower() == "chrome":
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox") # Required for running as root in some environments (e.g., Docker)
        options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
        options.add_argument("--window-size=1920,1080") # Set a consistent window size
        options.add_argument("--disable-gpu") # Recommended for headless mode
        options.add_argument("--log-level=3") # Suppress unnecessary logs

        # >>> MODIFIED FOR RENDER/CLOUD DEPLOYMENT TO USE WEBDriver_MANAGER <<<
        # This will automatically download the correct chromedriver executable
        # and set its path for Selenium.
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver # Return driver directly if successful
        except Exception as e:
            print(f"Error initializing Chrome WebDriver with WebDriverManager: {e}")
            raise # Re-raise the exception to propagate it

    elif browser_type.lower() == "firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox") # Add for Firefox too for consistency
        options.add_argument("--disable-dev-shm-usage") # Add for Firefox too for consistency

        # >>> MODIFIED FOR RENDER/CLOUD DEPLOYMENT TO USE WEBDriver_MANAGER <<<
        # This will automatically download the correct geckodriver executable
        try:
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            return driver # Return driver directly if successful
        except Exception as e:
            print(f"Error initializing Firefox WebDriver with WebDriverManager: {e}")
            raise # Re-raise the exception to propagate it

    else:
        raise ValueError("Unsupported browser type. Choose 'chrome' or 'firefox'.")

# Your __main__ block is fine for testing once the above is fixed.
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