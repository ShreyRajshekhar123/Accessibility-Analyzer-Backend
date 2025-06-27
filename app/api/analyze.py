# backend/app/api/analyze.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import HttpUrl
from typing import List
import datetime
import asyncio # Required for asyncio.gather

# Import your schemas (data models)
from ..schemas import AnalysisRequest, AnalysisResult, Issue, AnalysisSummary, AiSuggestion

# Import services for browser automation and Axe scanning
from ..services.browser import get_webdriver
from ..services.axe_runner import run_axe_scan
from ..services.ai_helper import get_ai_suggestions 

# Import your custom accessibility rules
from ..rules.alt_text import check_alt_text
from ..rules.headings import check_heading_structure
from ..rules.labels import check_form_labels
from ..rules.contrast import check_color_contrast
from ..rules.empty_interactive import check_empty_interactive_elements
from ..rules.document_language import check_document_language
from ..rules.descriptive_link_text import check_descriptive_link_text
from ..rules.media_captions import check_media_captions # NEW: Import the new custom rule

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_url(request: AnalysisRequest = Body(...)):
    """
    Analyzes a given URL for accessibility issues using:
    1. Selenium for headless browser automation.
    2. Axe-core via axe-selenium-python for automated accessibility checks.
    3. Custom BeautifulSoup rules (e.g., alt text, heading structure, form labels, color contrast, empty interactive elements, document language, descriptive link text, media captions) for additional static HTML checks.
    4. Gemini API for AI-powered fix suggestions (currently active).

    Args:
        request (AnalysisRequest): A Pydantic model containing the URL to analyze.

    Returns:
        AnalysisResult: A Pydantic model containing the analysis summary and a list of detected issues,
                        each potentially with AI-generated suggestions.

    Raises:
        HTTPException: If an error occurs during the analysis process.
    """
    url = request.url
    print(f"Received request to analyze URL: {url}")

    driver = None
    issues: List[Issue] = []
    # Initialize summary with zero counts before analysis starts, and score
    summary = AnalysisSummary(total_issues=0, critical=0, moderate=0, minor=0, score=100) # Initialize score to 100
    page_html_content = ""

    try:
        # Step 1: Initialize headless browser
        driver = get_webdriver("chrome")
        
        # Step 2: Navigate to the URL and get page HTML
        driver.get(str(url)) 
        page_html_content = driver.page_source 

        # Step 3: Run Axe-core accessibility scan
        axe_violations_raw = run_axe_scan(driver)
        for viol in axe_violations_raw:
            issues.append(Issue(**viol)) 

        # Step 4: Run Custom BeautifulSoup rules
        issues.extend(check_alt_text(page_html_content))          
        issues.extend(check_heading_structure(page_html_content)) 
        issues.extend(check_form_labels(page_html_content))       
        issues.extend(check_color_contrast(page_html_content))    
        issues.extend(check_empty_interactive_elements(page_html_content))
        issues.extend(check_document_language(page_html_content))
        issues.extend(check_descriptive_link_text(page_html_content))
        issues.extend(check_media_captions(page_html_content)) # NEW: Call the new custom rule

        # Step 5: Generate AI suggestions for each detected issue
        tasks = []
        for issue in issues:
            problematic_html = issue.nodes[0].html if issue.nodes else ""
            tasks.append(get_ai_suggestions(issue.description, issue.help, problematic_html))
        
        ai_suggestions_results = await asyncio.gather(*tasks)

        for i, suggestion_data in enumerate(ai_suggestions_results):
            issues[i].ai_suggestions = AiSuggestion(**suggestion_data)


        # Step 6: Calculate the comprehensive analysis summary and accessibility score
        summary.total_issues = len(issues)
        
        # Initialize deductions
        critical_deduction = 0
        moderate_deduction = 0
        minor_deduction = 0

        # Define weights for score calculation (Adjusted for less aggressive deductions)
        # You can tune these values based on how impactful each severity should be on the score.
        CRITICAL_WEIGHT = 5  # Reduced from 10
        MODERATE_WEIGHT = 2  # Reduced from 5
        MINOR_WEIGHT = 1     # Reduced from 2

        for issue in issues:
            if issue.severity == "critical":
                summary.critical += 1
                critical_deduction += CRITICAL_WEIGHT
            elif issue.severity in ["serious", "moderate"]: 
                summary.moderate += 1
                moderate_deduction += MODERATE_WEIGHT
            elif issue.severity == "minor":
                summary.minor += 1
                minor_deduction += MINOR_WEIGHT

        # Calculate the score
        calculated_score = 100 - (critical_deduction + moderate_deduction + minor_deduction)
        summary.score = max(0, calculated_score) # Ensure score doesn't go below 0

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
