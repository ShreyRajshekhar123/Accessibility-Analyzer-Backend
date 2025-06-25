from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
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
        # Suppress WebDriverManager logs (optional, makes output cleaner)
        os.environ['WDM_LOG_LEVEL'] = '0' # Suppress logs for webdriver-manager
        try:
            service = webdriver.ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error initializing Chrome WebDriver: {e}")
            # Fallback or raise specific error
            raise
    elif browser_type.lower() == "firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")
        os.environ['WDM_LOG_LEVEL'] = '0' # Suppress logs for webdriver-manager
        try:
            service = webdriver.FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
        except Exception as e:
            print(f"Error initializing Firefox WebDriver: {e}")
            raise
    else:
        raise ValueError("Unsupported browser type. Choose 'chrome' or 'firefox'.")

    return driver

if __name__ == "__main__":
    # Simple test to verify driver setup
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