# backend/app/core/analyzer.py

import logging
import asyncio
from typing import List, Tuple, Dict, Any, Optional
from pydantic import HttpUrl
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver # For type hinting

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
from ..rules.media_captions import check_media_captions

# Import your schemas (data models)
from ..schemas import Issue, AiSuggestion, IssueNode

logger = logging.getLogger("accessibility_analyzer_backend.core.analyzer")

async def run_full_analysis(url: HttpUrl) -> Tuple[List[Issue], str, str]:
    """
    Orchestrates the full accessibility analysis process for a given URL.
    This includes:
    1. Browser automation (loading page, getting HTML).
    2. Running Axe-core scan.
    3. Running custom accessibility rules.
    4. Fetching AI suggestions for identified issues.

    Args:
        url (HttpUrl): The URL of the page to analyze.

    Returns:
        Tuple[List[Issue], str, str]: A tuple containing:
            - A list of identified accessibility issues (with AI suggestions if fetched).
            - The full HTML content of the analyzed page.
            - The title of the analyzed page.
    """
    driver: Optional[WebDriver] = None
    issues_list: List[Issue] = []
    page_html_content = ""
    page_title = "N/A"

    try:
        logger.info(f"Starting WebDriver for URL: {url}")
        driver = get_webdriver("chrome") # Or configurable browser type
        driver.get(str(url))
        page_html_content = driver.page_source
        logger.info(f"Successfully loaded page content for URL: {url}")

        # Extract page title
        try:
            soup = BeautifulSoup(page_html_content, 'lxml')
            page_title_tag = soup.find('title')
            if page_title_tag and page_title_tag.string:
                page_title = page_title_tag.string.strip()
                logger.info(f"Extracted page title: '{page_title}' for URL: {url}")
        except Exception as title_e:
            logger.warning(f"Failed to extract page title for URL: {url}. Error: {title_e}")

        # --- Run Axe-core scan ---
        logger.info(f"Running Axe-core scan for URL: {url}")
        axe_violations_raw = run_axe_scan(driver)
        logger.info(f"Axe-core scan completed. Found {len(axe_violations_raw)} raw violations.")

        for viol in axe_violations_raw:
            try:
                parsed_nodes = []
                for node_data in viol.get('nodes', []):
                    parsed_nodes.append(IssueNode(
                        html=node_data.get('html'),
                        target=node_data.get('target', []),
                        snippet=node_data.get('snippet'),
                        failureSummary=node_data.get('failureSummary'),
                        xpath=node_data.get('xpath')
                    ))

                issues_list.append(Issue(
                    id=viol.get('id', 'unknown-id'),
                    description=viol.get('description', 'No description'),
                    help=viol.get('help', 'No help provided'),
                    helpUrl=viol.get('helpUrl'),
                    severity=viol.get('impact', 'minor'), # Axe-core uses 'impact' for severity
                    tags=viol.get('tags', []),
                    nodes=parsed_nodes
                ))
            except Exception as e:
                logger.error(f"Error parsing Axe violation into Issue schema: {e}. Violation: {viol}")
                logger.debug(traceback.format_exc()) # Only import traceback if needed, for production might remove
                # Decide if you want to skip this malformed issue or raise an error

        # --- Run custom rules ---
        logger.info("Running custom accessibility rules.")
        custom_rule_checks = [
            check_alt_text(page_html_content),
            check_heading_structure(page_html_content),
            check_form_labels(page_html_content),
            check_color_contrast(page_html_content),
            check_empty_interactive_elements(page_html_content),
            check_document_language(page_html_content),
            check_descriptive_link_text(page_html_content),
            check_media_captions(page_html_content),
        ]

        for rule_issues in custom_rule_checks:
            if rule_issues:
                issues_list.extend(rule_issues)
                logger.info(f"Added {len(rule_issues)} issues from a custom rule.")

        logger.info(f"Total issues after custom rules: {len(issues_list)}")

        # --- Fetch AI suggestions concurrently ---
        ai_suggestion_tasks = []
        for issue in issues_list:
            # Ensure nodes and their properties are safely accessed
            # Pass only relevant text to AI helper to save tokens/cost
            problematic_html = issue.nodes[0].html if issue.nodes and issue.nodes[0].html else ""
            ai_suggestion_tasks.append(get_ai_suggestions(issue.description, issue.help, problematic_html))

        if ai_suggestion_tasks:
            logger.info(f"Fetching AI suggestions for {len(ai_suggestion_tasks)} issues.")
            ai_suggestions_results = await asyncio.gather(*ai_suggestion_tasks, return_exceptions=True)

            for i, suggestion_data in enumerate(ai_suggestions_results):
                if isinstance(suggestion_data, Exception):
                    logger.error(f"AI Suggestion Error for issue {i}: {suggestion_data}")
                    logger.debug(traceback.format_exc())
                    issues_list[i].ai_suggestions = None
                else:
                    try:
                        issues_list[i].ai_suggestions = AiSuggestion(**suggestion_data)
                    except Exception as e:
                        logger.error(f"Error parsing AI suggestion data for issue {i}: {e}. Data: {suggestion_data}")
                        logger.debug(traceback.format_exc())
                        issues_list[i].ai_suggestions = None
            logger.info("AI suggestion fetching completed.")
        else:
            logger.info("No issues found, skipping AI suggestion fetching.")

        return issues_list, page_html_content, page_title

    except Exception as e:
        logger.critical(f"CRITICAL Analysis Core Error: An unhandled exception occurred during analysis of {url}. Error: {e}")
        logger.error(traceback.format_exc()) # Import traceback if not already
        raise # Re-raise the exception to be caught by the API endpoint

    finally:
        if driver:
            logger.info(f"Quitting WebDriver for URL: {url}")
            driver.quit()