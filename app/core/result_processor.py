# backend/app/core/result_processor.py

import logging
import datetime
from typing import List
from pydantic import HttpUrl

# Import your schemas (data models)
from ..schemas import AnalysisResult, Issue, AnalysisSummary

logger = logging.getLogger("accessibility_analyzer_backend.core.result_processor")

def calculate_accessibility_score(issues: List[Issue]) -> AnalysisSummary:
    """
    Calculates the accessibility score and categorizes issues based on their severity.
    """
    # Initialize AnalysisSummary with the new field names
    summary = AnalysisSummary(total_issues=len(issues), criticalIssues=0, moderateIssues=0, minorIssues=0, score=100)

    critical_deduction = 0
    moderate_deduction = 0
    minor_deduction = 0

    CRITICAL_WEIGHT = 5
    MODERATE_WEIGHT = 2
    MINOR_WEIGHT = 1

    for issue in issues:
        # Use .get to safely access severity, or default to "minor" if not present
        severity = issue.severity if hasattr(issue, 'severity') else "minor"
        
        if severity == "critical":
            summary.criticalIssues += 1 # Updated to criticalIssues
            critical_deduction += CRITICAL_WEIGHT
        elif severity in ["serious", "moderate"]: # Axe-core often uses 'serious' for higher impact
            summary.moderateIssues += 1 # Updated to moderateIssues
            moderate_deduction += MODERATE_WEIGHT
        elif severity == "minor":
            summary.minorIssues += 1 # Updated to minorIssues
            minor_deduction += MINOR_WEIGHT
        # Add 'impact' values that might map to 'minor' if axe-core specific
        elif severity == "low": # Axe-core also has 'low' impact
            summary.minorIssues += 1 # Updated to minorIssues
            minor_deduction += MINOR_WEIGHT


    calculated_score = 100 - (critical_deduction + moderate_deduction + minor_deduction)
    summary.score = max(0, calculated_score) # Ensure score doesn't go below 0
    
    logger.info(f"Score Calculation: Total Issues={summary.total_issues}, Critical={summary.criticalIssues}, " # Updated logger to criticalIssues
                f"Moderate={summary.moderateIssues}, Minor={summary.minorIssues}, Final Score={summary.score}") # Updated logger
    
    return summary

def process_analysis_data(
    url: HttpUrl,
    user_id: str,
    issues_list: List[Issue],
    page_html_content: str, # Not directly stored in AnalysisResult, but could be useful for debugging/future
    page_title: str
) -> AnalysisResult:
    """
    Combines all analysis components into a final AnalysisResult object.

    Args:
        url (HttpUrl): The URL that was analyzed.
        user_id (str): The ID of the user who requested the analysis.
        issues_list (List[Issue]): List of identified issues with AI suggestions.
        page_html_content (str): The full HTML content of the analyzed page (for potential future use).
        page_title (str): The title of the analyzed page.

    Returns:
        AnalysisResult: A complete Pydantic model representing the analysis report.
    """
    logger.info(f"Processing analysis data for URL: {url} | User: {user_id}")

    # Calculate summary and score based on the issues
    summary = calculate_accessibility_score(issues_list)

    # Create the final AnalysisResult object
    analysis_result = AnalysisResult(
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        summary=summary,
        issues=issues_list,
        page_title=page_title,
        user_id=user_id
    )
    
    logger.info(f"Analysis result processed for URL: {url}. Score: {summary.score}")
    return analysis_result