# backend/app/api/analyze.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import HttpUrl
from typing import List
import datetime

# Import your schemas (data models)
from ..schemas import AnalysisRequest, AnalysisResult, Issue, AnalysisSummary

# Import services for browser automation and Axe scanning
from ..services.browser import get_webdriver
from ..services.axe_runner import run_axe_scan

# Import your custom accessibility rules
from ..rules.alt_text import check_alt_text
# from ..rules.headings import check_heading_structure # Uncomment when you create this file and function
# from ..rules.labels import check_form_labels # Uncomment when you create this file and function
# from ..rules.contrast import check_color_contrast # Uncomment when you create this file and function

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_url(request: AnalysisRequest = Body(...)):
    """
    Analyzes a given URL for accessibility issues using:
    1. Selenium for headless browser automation.
    2. Axe-core via axe-selenium-python for automated accessibility checks.
    3. Custom BeautifulSoup rules for additional WCAG-based static HTML checks.

    Args:
        request (AnalysisRequest): A Pydantic model containing the URL to analyze.

    Returns:
        AnalysisResult: A Pydantic model containing the analysis summary and a list of detected issues.

    Raises:
        HTTPException: If an error occurs during the analysis process.
    """
    url = request.url
    print(f"Received request to analyze URL: {url}")

    driver = None
    issues: List[Issue] = []
    # Initialize summary with zero counts
    summary = AnalysisSummary(total_issues=0, critical=0, moderate=0, minor=0)
    page_html_content = "" # Variable to store the full HTML for custom rules

    try:
        # Step 1: Initialize headless browser (e.g., Chrome)
        # The browser will run in the background without a visible UI.
        driver = get_webdriver("chrome") 
        
        # Step 2: Navigate to the specified URL
        # Convert Pydantic's HttpUrl object to a string for Selenium's get() method.
        driver.get(str(url)) 

        # Retrieve the full HTML content of the page after it has loaded.
        # This HTML will be used by our custom BeautifulSoup rules.
        page_html_content = driver.page_source 

        # Step 3: Run Axe-core accessibility scan
        # axe-selenium-python will inject axe-core into the loaded page
        # and execute its automated checks.
        axe_violations_raw = run_axe_scan(driver)
        
        # Convert the raw violations from axe-core into our standardized Issue schema.
        for viol in axe_violations_raw:
            # The Issue schema should match the structure provided by run_axe_scan
            issues.append(Issue(**viol)) 

        # Step 4: Run Custom BeautifulSoup rules
        # These rules perform additional static analysis on the HTML content.
        # Each custom rule function will return a list of Issue objects,
        # which are then extended to the main issues list.
        issues.extend(check_alt_text(page_html_content))
        # Uncomment and add more custom rule checks as you implement them in backend/app/rules/
        # issues.extend(check_heading_structure(page_html_content))
        # issues.extend(check_form_labels(page_html_content))
        # issues.extend(check_color_contrast(page_html_content))

        # Step 5: Calculate the analysis summary based on all collected issues (Axe + Custom)
        summary.total_issues = len(issues)
        for issue in issues:
            # Map Axe's 'impact' levels ('serious') to your schema's 'severity' ('moderate')
            if issue.severity == "critical":
                summary.critical += 1
            elif issue.severity in ["serious", "moderate"]: # Map 'serious' from axe to 'moderate' in your summary
                summary.moderate += 1
            elif issue.severity == "minor":
                summary.minor += 1

    except Exception as e:
        # Catch any exceptions that occur during the analysis (e.g., WebDriver issues, network errors)
        print(f"Error during analysis of {url}: {e}")
        # Raise an HTTPException to return a proper error response to the client
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # Ensure the browser is always closed, even if an error occurs,
        # to prevent lingering browser processes.
        if driver:
            driver.quit() 

    # Return the complete analysis result
    return AnalysisResult(
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), # Current UTC timestamp
        summary=summary,
        issues=issues
    )
