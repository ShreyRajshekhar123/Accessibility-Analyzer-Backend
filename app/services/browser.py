# app/services/browser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

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

        # >>> NEW CRUCIAL LINE HERE <<<
        # This tells Selenium where to find the Chrome browser executable on Render.
        # It's usually '/usr/bin/chromium-browser' for Render's native environments.
        # You could also get this from an environment variable (e.g., os.getenv("CHROMIUM_PATH"))
        # if you prefer, but directly setting it is common for this known path.
        options.binary_location = "/usr/bin/chromium-browser" #

        try:
            # Use ChromeDriverManager to automatically download and manage the ChromeDriver executable
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            print(f"Error initializing Chrome WebDriver with WebDriverManager: {e}")
            raise

    elif browser_type.lower() == "firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # >>> NEW CRUCIAL LINE HERE FOR FIREFOX (if you use it) <<<
        # This tells Selenium where to find the Firefox browser executable on Render.
        # This path might vary, but for now, we'll keep it for completeness.
        # You might need to confirm the actual path if you use Firefox.
        options.binary_location = "/usr/bin/firefox" # Common path, verify for Render

        try:
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            return driver
        except Exception as e:
            print(f"Error initializing Firefox WebDriver with WebDriverManager: {e}")
            raise

    else:
        raise ValueError("Unsupported browser type. Choose 'chrome' or 'firefox'.")

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