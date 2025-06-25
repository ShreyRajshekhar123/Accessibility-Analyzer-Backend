# backend/app/rules/alt_text.py

from bs4 import BeautifulSoup
from typing import List, Dict, Any
from ..schemas import Issue, IssueNode, AiSuggestion

def check_alt_text(html_content: str) -> List[Issue]:
    """
    Checks for images with missing or empty alt text.

    Args:
        html_content (str): The full HTML content of the page to analyze.

    Returns:
        List[Issue]: A list of Issue objects for images missing alt text.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Find all <img> tags in the HTML content
    images = soup.find_all('img')

    for img in images:
        alt_text = img.get('alt')
        
        # Check if the 'alt' attribute is missing OR if it's present but empty/whitespace only
        if alt_text is None or not alt_text.strip():
            # If an issue is found, create an Issue object
            issue = Issue(
                id="custom-image-alt-missing",
                description="Images must have meaningful alternate text for accessibility.",
                help="Provide a concise and descriptive alt attribute for all images. If the image is purely decorative, use `alt=\"\"` (empty alt text).",
                severity="critical", # Images without alt text can be critical for screen reader users
                nodes=[
                    IssueNode(
                        html=str(img), # Store the full HTML tag of the problematic image
                        target=[img.name] # The tag name, e.g., 'img'
                    )
                ],
                ai_suggestions=AiSuggestion(
                    short_fix="Add descriptive alt text to the image.",
                    detailed_fix=f"For the image: `{str(img)}`, add a descriptive `alt` attribute that conveys the image's purpose or content. For example, if it's a company logo, use `<img src='...' alt='Company Logo'>`. If the image serves no functional purpose and is purely decorative, set `alt=''` to hide it from screen readers."
                )
            )
            issues.append(issue)
    return issues

# This __main__ block is for local testing of this specific rule file.
# It will not run when the module is imported by FastAPI.
if __name__ == "__main__":
    print("--- Testing backend/app/rules/alt_text.py locally ---")

    # Example 1: HTML with a good alt text
    html_good = "<html><body><img src='a.png' alt='A meaningful description'></body></html>"
    issues_good = check_alt_text(html_good)
    print(f"\nGood HTML (expected 0 issues): Found {len(issues_good)} issues.")
    if issues_good:
        print("Issues found:")
        for issue in issues_good:
            print(issue.json(indent=2))

    # Example 2: HTML with a missing alt text
    html_bad_missing = "<html><body><img src='b.png'></body></html>"
    issues_missing = check_alt_text(html_bad_missing)
    print(f"\nMissing Alt HTML (expected 1 issue): Found {len(issues_missing)} issues.")
    if issues_missing:
        print("Issues found:")
        for issue in issues_missing:
            print(issue.json(indent=2))

    # Example 3: HTML with an empty alt text (which is valid for decorative images, but our rule checks for non-decorative as well)
    # Note: Our rule detects this as an issue because 'alt=" "' is effectively empty.
    # A true decorative image should have alt=""
    html_bad_empty = "<html><body><img src='c.png' alt=' '></body></html>"
    issues_empty = check_alt_text(html_bad_empty)
    print(f"\nEmpty Alt HTML (expected 1 issue): Found {len(issues_empty)} issues.")
    if issues_empty:
        print("Issues found:")
        for issue in issues_empty:
            print(issue.json(indent=2))

    # Example 4: Mixed HTML with one good and one bad image
    html_mixed = "<html><body><img src='d.png' alt='valid logo'><img src='e.png'></body></html>"
    issues_mixed = check_alt_text(html_mixed)
    print(f"\nMixed HTML (expected 1 issue): Found {len(issues_mixed)} issues.")
    if issues_mixed:
        print("Issues found:")
        for issue in issues_mixed:
            print(issue.json(indent=2))
