# app/services/browser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
# from webdriver_manager.chrome import ChromeDriverManager # REMOVE THIS
# from webdriver_manager.firefox import GeckoDriverManager # REMOVE THIS
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

        # >>> CRUCIAL CHANGES FOR RENDER/CLOUD DEPLOYMENT <<<
        # Get Chrome binary path from environment variable set by Render buildpack
        chrome_binary_path = os.getenv("GOOGLE_CHROME_BIN")
        if chrome_binary_path:
            options.binary_location = chrome_binary_path
        else:
            # This 'else' block is for local development if you still want to use webdriver_manager
            # or for a more robust error handling if the env var isn't set.
            # On Render, this path should always be set by the buildpack.
            print("WARNING: GOOGLE_CHROME_BIN environment variable not found. Relying on local Chrome installation or WebDriverManager.")
            # If you *must* have webdriver_manager for local development AND Render,
            # you'd put the webdriver_manager install here, but it's often better
            # to have separate logic or a dedicated dev setup.
            # For Render, the buildpack *must* provide this.

        # Get ChromeDriver path from environment variable set by Render buildpack
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if chromedriver_path:
            service = webdriver.ChromeService(executable_path=chromedriver_path)
        else:
            # Similar to above, this 'else' is for local development or robust error.
            # On Render, this path should always be set by the buildpack.
            print("WARNING: CHROMEDRIVER_PATH environment variable not found. Relying on local ChromeDriver or WebDriverManager.")
            # If you *must* have webdriver_manager for local development AND Render,
            # you'd put the webdriver_manager install here.
            # service = webdriver.ChromeService(ChromeDriverManager().install()) # Use this ONLY for local if needed
            raise EnvironmentError("CHROMEDRIVER_PATH environment variable not set. Cannot find ChromeDriver for Render deployment.")

        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error initializing Chrome WebDriver: {e}")
            raise
    elif browser_type.lower() == "firefox":
        options = FirefoxOptions()
        options.add_argument("--headless")

        # >>> CRUCIAL CHANGES FOR RENDER/CLOUD DEPLOYMENT (Firefox equivalent) <<<
        # If you were to use Firefox on Render, you'd need similar buildpacks
        # and environment variable checks for Firefox binary and geckodriver.
        # For simplicity, if you're primarily using Chrome, you can ignore this for now.
        firefox_binary_path = os.getenv("FIREFOX_BIN") # Example env var
        if firefox_binary_path:
            options.binary_location = firefox_binary_path

        geckodriver_path = os.getenv("GECKODRIVER_PATH") # Example env var
        if geckodriver_path:
            service = webdriver.FirefoxService(executable_path=geckodriver_path)
        else:
            # service = webdriver.FirefoxService(GeckoDriverManager().install()) # Use this ONLY for local if needed
            raise EnvironmentError("GECKODRIVER_PATH environment variable not set. Cannot find GeckoDriver for Render deployment.")

        try:
            driver = webdriver.Firefox(service=service, options=options)
        except Exception as e:
            print(f"Error initializing Firefox WebDriver: {e}")
            raise
    else:
        raise ValueError("Unsupported browser type. Choose 'chrome' or 'firefox'.")

    return driver

if __name__ == "__main__":
    # Simple test to verify driver setup
    # Note: This __main__ block might still fail locally if you don't have
    # GOOGLE_CHROME_BIN/CHROMEDRIVER_PATH set locally or if you've removed
    # webdriver_manager entirely for local testing.
    # For robust local testing, you might want to wrap this in a check
    # for being on Render vs. local.
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