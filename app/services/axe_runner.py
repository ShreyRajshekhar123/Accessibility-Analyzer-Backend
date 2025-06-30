import logging
from typing import Dict, Any, List
from playwright.async_api import Page
import os

logger = logging.getLogger("accessibility_analyzer_backend.services.axe_runner")

# --- IMPORTANT: Axe-core JavaScript loading ---
# This block attempts to load the actual axe.min.js from your project's static directory.
# Ensure axe.min.js is placed in your 'static/js' folder directly under your 'backend' directory.

AXE_CORE_SCRIPT_CONTENT = ""
try:
    # Construct the absolute path to axe.min.js
    # This file (axe_runner.py) is in /app/services/
    # To get to the project root (backend folder), we go up two directories (../../)
    # Then navigate into static/js/axe.min.js
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _axe_script_path = os.path.join(_current_dir, "..", "..", "static", "js", "axe.min.js")

    if os.path.exists(_axe_script_path):
        with open(_axe_script_path, "r", encoding="utf-8") as f:
            AXE_CORE_SCRIPT_CONTENT = f.read()
        logger.info(f"Loaded axe.min.js from: {_axe_script_path}")
    else:
        logger.error(f"axe.min.js not found at expected path: '{_axe_script_path}'. Axe-core scan will likely fail.")
except Exception as e:
    logger.error(f"Failed to load axe.min.js from disk: {e}. Axe-core scan will likely fail.")


async def run_axe_scan(page: Page) -> List[Dict[str, Any]]:
    """
    Runs an axe-core accessibility scan on the current Playwright page.
    Injects axe-core and then executes the scan.
    Returns a list of accessibility violations.
    """
    if not AXE_CORE_SCRIPT_CONTENT:
        logger.error("AXE_CORE_SCRIPT_CONTENT is empty. Axe-core cannot be injected or run. Returning empty results.")
        return [] # Return empty list if axe script is not loaded

    try:
        # Inject axe-core into the page context
        await page.add_script_tag(content=AXE_CORE_SCRIPT_CONTENT)
        logger.info("Axe-core script injected into the page.")

        # Run the axe-core scan within the browser context
        results = await page.evaluate("""
            async () => {
                // Ensure axe is defined before running
                if (typeof axe === 'undefined') {
                    console.error("axe is not defined on the page. Script injection might have failed.");
                    return null; // Explicitly return null if axe is not found
                }
                const results = await axe.run(document);
                return results;
            }
        """)

        # --- IMPORTANT: Handle potential NoneType from page.evaluate ---
        if results is None:
            logger.error("page.evaluate('axe.run()') returned None. Axe-core did not produce results. This often means axe.js wasn't loaded correctly or there was a JS error in axe.run().")
            return [] # Return an empty list to avoid AttributeError

        violations = results.get('violations', [])
        logger.info(f"Axe-core scan completed. Found {len(violations)} raw violations.")

        # Format violations to match your Issue schema
        formatted_issues = []
        for violation in violations:
            nodes_data = []
            for node in violation.get('nodes', []):
                nodes_data.append({
                    "html": node.get('html'),
                    "target": node.get('target', []),
                    "snippet": node.get('snippet'),
                    "failureSummary": node.get('failureSummary'),
                    "xpath": node.get('xpath') # axe-core provides xpath in nodes
                })

            formatted_issues.append({
                "id": violation.get('id', 'unknown'),
                "description": violation.get('description', 'No description'),
                "help": violation.get('help', 'No help message'),
                "helpUrl": violation.get('helpUrl'),
                "severity": violation.get('impact', 'minor'), # axe uses 'impact' (critical, serious, moderate, minor)
                "tags": violation.get('tags', []),
                "nodes": nodes_data,
                # "ai_suggestions": None # Will be populated later in analyzer.py
            })
        return formatted_issues
    except Exception as e:
        logger.error(f"Error running Axe-core scan with Playwright: {e}", exc_info=True)
        raise # Re-raise the exception after logging for upstream handling

if __name__ == "__main__":
    import asyncio
    # Ensure these imports are correct relative to your project structure if you use this test block
    from accessibility_analyzer_backend.services.browser import get_browser_context_and_page, close_browser_context, close_playwright_browser_instances

    async def test_axe_scan():
        context, page = None, None
        try:
            print("Testing Axe scan on example.com with Playwright...")
            context, page = await get_browser_context_and_page("chromium")
            
            # Use a simple page that is less likely to have anti-bot measures
            await page.goto("http://www.example.com", wait_until="domcontentloaded", timeout=60000)
            
            violations = await run_axe_scan(page)
            
            print(f"Found {len(violations)} accessibility violations.")
            if violations:
                print("First violation:", violations[0])
            else:
                print("No violations found.")
        except Exception as e:
            print(f"An error occurred during Axe scan test: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debug
        finally:
            if context:
                await close_browser_context(context)
            await close_playwright_browser_instances() # Ensure Playwright is stopped

    asyncio.run(test_axe_scan())