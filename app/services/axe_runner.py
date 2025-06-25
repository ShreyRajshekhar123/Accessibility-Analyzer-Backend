from axe_selenium_python import Axe
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Dict, Any, List

def run_axe_scan(driver: WebDriver) -> List[Dict[str, Any]]:
    """
    Runs an axe-core accessibility scan on the current page loaded in the WebDriver.
    Returns a list of accessibility violations.
    """
    axe = Axe(driver)
    # Inject axe-core into the page
    axe.inject()
    # Run the accessibility scan
    # You can customize rules here if needed, e.g., .run(options={'runOnly': {'type': 'tag', 'values': ['wcag2a', 'wcag2aa']}})
    results = axe.run()

    # axe-selenium-python returns a dictionary with 'violations', 'passes', 'incomplete', ' inapplicable'
    # We are primarily interested in 'violations' for reporting issues.
    violations = results.get('violations', [])

    # Format violations to match your Issue schema
    formatted_issues = []
    for violation in violations:
        nodes_data = []
        for node in violation.get('nodes', []):
            # 'html' and 'target' are directly available
            nodes_data.append({
                "html": node.get('html'),
                "target": node.get('target', [])
            })

        formatted_issues.append({
            "id": violation.get('id', 'unknown'),
            "description": violation.get('description', 'No description'),
            "help": violation.get('help', 'No help message'),
            "severity": violation.get('impact', 'minor'), # axe uses 'impact' (critical, serious, moderate, minor)
            "nodes": nodes_data,
            "ai_suggestions": None # Will be populated in Phase 4
        })
    return formatted_issues

if __name__ == "__main__":
    # This part is for local testing of axe_runner.py
    # You would typically call this from your main analysis logic
    from .browser import get_webdriver # Import here for local test only

    print("Testing Axe scan on example.com with Chrome...")
    driver = None
    try:
        driver = get_webdriver("chrome")
        driver.get("http://www.example.com") # Load a page to scan
        violations = run_axe_scan(driver)
        print(f"Found {len(violations)} accessibility violations.")
        if violations:
            print("First violation:", violations[0])
        else:
            print("No violations found.")
    except Exception as e:
        print(f"An error occurred during Axe scan test: {e}")
    finally:
        if driver:
            driver.quit()