import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext # Import necessary Playwright classes
from typing import Literal, Tuple, Dict, Any

logger = logging.getLogger("accessibility_analyzer_backend.services.browser")

# Global Playwright instance to manage browsers
_playwright_instance = None
_browser_cache: Dict[str, Browser] = {}

async def get_browser_context_and_page(
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
) -> Tuple[BrowserContext, Page]:
    """
    Launches a browser (Chromium, Firefox, or WebKit) and returns a new
    browser context and page. This function now handles the Playwright lifecycle.
    """
    global _playwright_instance
    global _browser_cache

    if _playwright_instance is None:
        _playwright_instance = await async_playwright().start()

    browser = _browser_cache.get(browser_type)
    if not browser or not browser.is_connected():
        logger.info(f"Launching new Playwright {browser_type} browser...")
        try:
            if browser_type == "chromium":
                browser = await _playwright_instance.chromium.launch(headless=True, args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ])
            elif browser_type == "firefox":
                browser = await _playwright_instance.firefox.launch(headless=True, args=[
                    "--no-sandbox",
                ])
            elif browser_type == "webkit":
                browser = await _playwright_instance.webkit.launch(headless=True, args=[
                    "--no-sandbox",
                ])
            else:
                raise ValueError("Unsupported browser type. Choose 'chromium', 'firefox', or 'webkit'.")
            _browser_cache[browser_type] = browser
            logger.info(f"Playwright {browser_type} browser launched successfully.")
        except Exception as e:
            logger.error(f"Error launching Playwright {browser_type} browser: {e}")
            raise

    # Create a new isolated browser context for each analysis
    # This ensures a clean state (no shared cookies, local storage, etc.)
    context = await browser.new_context(viewport={"width": 1920, "height": 1080})
    page = await context.new_page()

    logger.info("New browser context and page created.")
    return context, page

async def close_browser_context(context: BrowserContext):
    """
    Closes the given Playwright browser context.
    """
    if context:
        logger.info("Closing Playwright browser context.")
        await context.close()

async def close_playwright_browser_instances():
    """
    Closes all cached Playwright browser instances and the Playwright API.
    This should be called when the application is shutting down.
    """
    global _playwright_instance
    global _browser_cache

    if _playwright_instance:
        logger.info("Closing all cached Playwright browser instances.")
        for browser_type, browser in list(_browser_cache.items()): # Iterate on a copy
            if browser.is_connected():
                await browser.close()
            del _browser_cache[browser_type] # Remove from cache

        logger.info("Stopping Playwright API.")
        await _playwright_instance.stop()
        _playwright_instance = None


# CLI test runner for Playwright
if __name__ == "__main__":
    import asyncio

    async def test_browsers():
        print("Testing Chromium headless browser...")
        context, page = None, None
        try:
            context, page = await get_browser_context_and_page("chromium")
            await page.goto("http://www.example.com")
            title = await page.title()
            print(f"Chromium Title: {title}")
            print("Chromium test successful.")
        except Exception as e:
            print(f"Chromium test failed: {e}")
        finally:
            if context:
                await close_browser_context(context)

        print("\nTesting Firefox headless browser...")
        context, page = None, None
        try:
            context, page = await get_browser_context_and_page("firefox")
            await page.goto("http://www.example.com")
            title = await page.title()
            print(f"Firefox Title: {title}")
            print("Firefox test successful.")
        except Exception as e:
            print(f"Firefox test failed: {e}")
        finally:
            if context:
                await close_browser_context(context)

        print("\nTesting WebKit headless browser...")
        context, page = None, None
        try:
            context, page = await get_browser_context_and_page("webkit")
            await page.goto("http://www.example.com")
            title = await page.title()
            print(f"WebKit Title: {title}")
            print("WebKit test successful.")
        except Exception as e:
            print(f"WebKit test failed: {e}")
        finally:
            if context:
                await close_browser_context(context)

        await close_playwright_browser_instances()


    asyncio.run(test_browsers())