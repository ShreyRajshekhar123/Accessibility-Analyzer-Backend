# backend/app/rules/descriptive_link_text.py

from bs4 import BeautifulSoup
from typing import List
from ..schemas import Issue, IssueNode, AiSuggestion

def check_descriptive_link_text(html_content: str) -> List[Issue]:
    """
    Checks for <a> elements that have non-descriptive link text such as
    "click here", "read more", "learn more", or variations thereof.
    This rule focuses on explicit text content and does not evaluate
    contextual descriptions unless provided via ARIA attributes.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Common non-descriptive phrases (case-insensitive)
    non_descriptive_phrases = [
        r'click here',
        r'read more',
        r'learn more',
        r'find out more',
        r'details',
        r'here',
        r'more'
    ]
    
    # Regex to match phrases, accounting for potential leading/trailing punctuation or spaces
    # Example: r'\bclick here\b' matches "click here" but not "unclick here"
    # We need to be careful with broad terms like 'more' or 'here'
    # For simplicity, we'll strip text and check for exact matches or very common patterns.
    
    # Find all <a> tags that have an href attribute and some text content (after stripping whitespace)
    links = soup.find_all('a', href=True)

    for link in links:
        link_text = link.get_text(strip=True).lower()
        
        # Skip links that have an aria-label or aria-labelledby, as these provide context
        if link.get('aria-label') or link.get('aria-labelledby'):
            continue
        
        # Check if the stripped text matches any of the non-descriptive phrases
        is_non_descriptive = False
        for phrase in non_descriptive_phrases:
            if link_text == phrase.replace(r'\b', '').strip() or \
                (phrase == r'more' and 'more' in link_text) or \
                (phrase == r'here' and 'here' in link_text) :
                is_non_descriptive = True
                break
        
        if is_non_descriptive:
            issue_html = str(link)
            issues.append(Issue(
                id="custom-non-descriptive-link-text",
                description="Link text is non-descriptive.",
                help="Link text should be meaningful and unique, describing the purpose or destination of the link without relying on surrounding content. Generic phrases like 'click here' or 'read more' are unhelpful for screen reader users navigating by a list of links.",
                severity="critical", # Can be moderate depending on context, but often critical for navigation
                nodes=[IssueNode(html=issue_html, target=["a"])],
                ai_suggestions=AiSuggestion(
                    short_fix="Revise link text to be descriptive of its destination or purpose.",
                    detailed_fix=f"The link: `{issue_html}` uses non-descriptive text ('{link_text}'). Change the link text to something that clearly indicates where the link leads or what action it performs. For example, instead of `<a href=\"/docs\">Read More</a>`, use `<a href=\"/docs\">Read our Documentation</a>`. If the link contains an icon, use `aria-label` to provide a descriptive name for screen readers, or visually hide the descriptive text within the link."
                )
            ))
    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/descriptive_link_text.py locally ---")

    # Test 1: Non-descriptive links (bad)
    html_bad_links = """
    <html><body>
        <a href=\"#\">click here</a>
        <a href=\"/about\">Read more</a>
        <a href=\"/help\">learn More</a>
        <a href=\"/product/details\">Details</a>
        <a href=\"/contact\">here</a>
        <a href=\"/another\">More</a>
    </body></html>
    """
    issues_bad_links = check_descriptive_link_text(html_bad_links)
    print(f"\nTest 1 (Bad Links): Found {len(issues_bad_links)} issues.")
    for issue in issues_bad_links:
        print(issue.json(indent=2))

    # Test 2: Descriptive links (good)
    html_good_links = """
    <html><body>
        <a href=\"/products\">View All Products</a>
        <a href=\"/download-report\">Download Annual Report</a>
        <a href=\"/login\" aria-label=\"Login to your account\">Sign In</a>
        <a href=\"/privacy\" aria-labelledby=\"privacy-link-text\"></a>
        <span id=\"privacy-link-text\">Privacy Policy</span>
    </body></html>
    """
    issues_good_links = check_descriptive_link_text(html_good_links)
    print(f"\nTest 2 (Good Links): Found {len(issues_good_links)} issues.")
    for issue in issues_good_links:
        print(issue.json(indent=2))

    # Test 3: Empty link (already handled by empty_interactive.py) - should not be caught here
    html_empty_link = "<html><body><a href=\"#\"></a></body></html>"
    issues_empty_link = check_descriptive_link_text(html_empty_link)
    print(f"\nTest 3 (Empty Link - ignored by this rule): Found {len(issues_empty_link)} issues.")
    for issue in issues_empty_link:
        print(issue.json(indent=2))
