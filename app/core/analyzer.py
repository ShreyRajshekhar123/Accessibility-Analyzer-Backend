import logging
import asyncio
import traceback
from typing import List, Tuple, Dict, Any, Optional
from pydantic import HttpUrl
from bs4 import BeautifulSoup

# Import services for browser automation and Axe scanning
from ..services.browser import get_browser_context_and_page, close_browser_context
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
from playwright.async_api import BrowserContext, Page # For type hinting

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
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    issues_list: List[Issue] = []
    page_html_content = ""
    page_title = "N/A"

    try:
        logger.info(f"Starting Playwright browser context and page for URL: {url}")
        # Use a context manager to ensure browser context is closed
        context, page = await get_browser_context_and_page("chromium") # Or configurable browser type
        
        await page.goto(str(url), wait_until="networkidle") # Wait for network to be idle
        page_html_content = await page.content() # Get full HTML content
        logger.info(f"Successfully loaded page content for URL: {url}")

        # Extract page title using Playwright's API
        try:
            page_title = await page.title()
            if page_title:
                page_title = page_title.strip()
                logger.info(f"Extracted page title: '{page_title}' for URL: {url}")
            else:
                page_title = "N/A" # Fallback if title is empty
        except Exception as title_e:
            logger.warning(f"Failed to extract page title for URL: {url}. Error: {title_e}")
            page_title = "N/A" # Ensure page_title is set even on error

        # --- Run Axe-core scan ---
        logger.info(f"Running Axe-core scan for URL: {url}")
        axe_violations_raw = await run_axe_scan(page) # Await the async function
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
                logger.debug(traceback.format_exc())

        # --- Run custom rules ---
        logger.info("Running custom accessibility rules.")
        # Your custom rules still operate on the HTML content, which is good.
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
        logger.error(traceback.format_exc())
        raise

    finally:
        if context: # Check if context was successfully created
            logger.info(f"Closing Playwright browser context for URL: {url}")
            await close_browser_context(context)