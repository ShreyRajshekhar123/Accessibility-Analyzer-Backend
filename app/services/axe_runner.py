import logging
from typing import Dict, Any, List
from playwright.async_api import Page, BrowserContext # Import Page for type hinting

logger = logging.getLogger("accessibility_analyzer_backend.services.axe_runner")

# Axe-core JavaScript code (copy axe.min.js or load from CDN)
# For production, it's highly recommended to fetch the latest axe.min.js
# from a reliable CDN or bundle it locally.
# For simplicity, I'm providing a minimal placeholder, but you should
# use the actual axe.min.js content.
# You might want to download axe.min.js and put it in a 'static' or 'js' folder
# in your project, then read its content.
# Example: with open("path/to/axe.min.js", "r") as f: AXE_CORE_SCRIPT = f.read()
# For now, let's use a very basic dummy to demonstrate the structure.
# You MUST replace this with the actual axe-core script.
AXE_CORE_SCRIPT = """
if (typeof axe === 'undefined') {
    // This is a minimal placeholder for axe-core.
    // Replace this with the actual content of axe.min.js
    // For example: fetch('https://unpkg.com/axe-core@4.x.x/axe.min.js').then(r => r.text()).then(t => eval(t));
    // Or, include axe.min.js in your project and load its content here.
    var axe = {
        run: function(element, options, callback) {
            console.warn("Using dummy axe-core script. Please replace with actual axe.min.js content.");
            // Simulate a simple violation
            setTimeout(() => {
                const violations = [
                    {
                        id: "dummy-violation",
                        description: "This is a dummy accessibility violation.",
                        help: "Replace axe.min.js for real results.",
                        helpUrl: "https://www.deque.com/axe/core-documentation/api-documentation/#axe-core-tags",
                        impact: "critical",
                        tags: ["dummy", "test"],
                        nodes: [
                            {
                                html: "<body>...</body>",
                                target: ["body"],
                                snippet: "<body>",
                                failureSummary: "Dummy failure summary",
                                xpath: "/html/body"
                            }
                        ]
                    }
                ];
                callback(null, { violations: violations });
            }, 100);
        }
    };
}
"""
# You would load the actual axe-core script like this:
try:
    # Assuming axe.min.js is in a 'static/js' directory at the root of your backend app
    # Adjust path as necessary relative to where this script is run or package structure
    import os
    _current_dir = os.path.dirname(__file__)
    _axe_script_path = os.path.join(_current_dir, "..", "..", "static", "js", "axe.min.js")
    if os.path.exists(_axe_script_path):
        with open(_axe_script_path, "r", encoding="utf-8") as f:
            AXE_CORE_SCRIPT = f.read()
        logger.info(f"Loaded axe.min.js from: {_axe_script_path}")
    else:
        logger.warning(f"axe.min.js not found at '{_axe_script_path}'. Using placeholder/CDN if available or default.")
        # Fallback to a CDN if you prefer, but local bundling is usually better for production stability
        # You might want to add a step to download axe.min.js during deployment if not packaged.
        # AXE_CORE_SCRIPT = "fetch('https://unpkg.com/axe-core@4.x.x/axe.min.js').then(r => r.text()).then(t => eval(t));"
except Exception as e:
    logger.error(f"Failed to load axe.min.js: {e}. Using placeholder.")


async def run_axe_scan(page: Page) -> List[Dict[str, Any]]:
    """
    Runs an axe-core accessibility scan on the current Playwright page.
    Injects axe-core and then executes the scan.
    Returns a list of accessibility violations.
    """
    try:
        # Inject axe-core into the page context
        # page.add_script_tag allows injecting JavaScript files or raw content
        await page.add_script_tag(content=AXE_CORE_SCRIPT)
        logger.info("Axe-core script injected into the page.")

        # Run the axe-core scan within the browser context
        # page.evaluate runs a JavaScript function in the page's context
        # and returns the result to Python.
        # axe.run() returns a Promise, so we await it in JS
        results = await page.evaluate("""
            async () => {
                // You can customize rules here if needed, e.g.,
                // const options = { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } };
                // const results = await axe.run(document, options);
                const results = await axe.run(document);
                return results;
            }
        """)

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
        logger.error(f"Error running Axe-core scan with Playwright: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    from .browser import get_browser_context_and_page, close_browser_context, close_playwright_browser_instances

    async def test_axe_scan():
        context, page = None, None
        try:
            print("Testing Axe scan on example.com with Playwright...")
            context, page = await get_browser_context_and_page("chromium")
            await page.goto("http://www.example.com") # Load a page to scan
            violations = await run_axe_scan(page)
            print(f"Found {len(violations)} accessibility violations.")
            if violations:
                print("First violation:", violations[0])
            else:
                print("No violations found.")
        except Exception as e:
            print(f"An error occurred during Axe scan test: {e}")
        finally:
            if context:
                await close_browser_context(context)
            await close_playwright_browser_instances() # Ensure Playwright is stopped

    asyncio.run(test_axe_scan())