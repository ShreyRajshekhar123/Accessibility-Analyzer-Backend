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
    Analyzes a given URL for accessibility issues using Selenium, Axe-core,
    and custom BeautifulSoup rules. AI-powered fix suggestions are currently
    not enabled in this version.
    """
    url = request.url
    print(f"Received request to analyze URL: {url}")

    driver = None
    issues: List[Issue] = []
    summary = AnalysisSummary(total_issues=0, critical=0, moderate=0, minor=0)
    page_html_content = "" # Variable to store the full HTML for custom rules

    try:
        # Step 1: Initialize headless browser
        driver = get_webdriver("chrome")
        
        # Step 2: Navigate to the URL and get page HTML
        driver.get(str(url)) 
        page_html_content = driver.page_source 

        # Step 3: Run Axe-core accessibility scan
        axe_violations_raw = run_axe_scan(driver)
        for viol in axe_violations_raw:
            # When converting raw Axe violations to Issue, ai_suggestions will default to None
            issues.append(Issue(**viol)) 

        # Step 4: Run Custom BeautifulSoup rules
        issues.extend(check_alt_text(page_html_content))
        # Add more custom rule checks here as you implement them

        # No AI suggestion generation here in this version.
        # The ai_suggestions field in the Issue schema will remain None.

        # Step 5: Calculate the analysis summary based on all collected issues (Axe + Custom)
        summary.total_issues = len(issues)
        for issue in issues:
            if issue.severity == "critical":
                summary.critical += 1
            elif issue.severity in ["serious", "moderate"]: 
                summary.moderate += 1
            elif issue.severity == "minor":
                summary.minor += 1

    except Exception as e:
        print(f"Error during analysis of {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if driver:
            driver.quit() 

    return AnalysisResult(
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        summary=summary,
        issues=issues
    )
