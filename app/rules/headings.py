# backend/app/rules/headings.py

from bs4 import BeautifulSoup
from typing import List, Dict, Any
from ..schemas import Issue, IssueNode, AiSuggestion

def check_heading_structure(html_content: str) -> List[Issue]:
    """
    Checks for common heading structure issues (missing H1, skipped heading levels).
    Note: This is a simplified check. Comprehensive heading validation is complex
    and would require more sophisticated DOM traversal and state tracking.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Rule 1: Check for missing H1
    h1_tags = soup.find_all('h1')
    if not h1_tags:
        issues.append(Issue(
            id="custom-missing-h1",
            description="Page should have at least one H1 heading.",
            help="The H1 heading defines the main topic or purpose of the page and is crucial for screen reader users to understand the page's structure. It should be unique and descriptive.",
            severity="critical",
            nodes=[IssueNode(html="<html>...</html>", target=["html"])], # Target the whole page as H1 is a page-level concept
            ai_suggestions=AiSuggestion(
                short_fix="Add an H1 heading.",
                detailed_fix="Ensure the primary title or main content heading of the page is marked with an `<h1>` tag. For single-page applications or dynamic content, ensure the main heading is updated appropriately. If there's no visual H1, consider adding a visually hidden `<h1>` (e.g., `<h1 class='sr-only'>Page Title</h1>`) for screen reader users."
            )
        ))
    # Optionally, you could add a rule here for too many H1s, though Axe often catches issues related to multiple main landmarks.
    # elif len(h1_tags) > 1:
    #     issues.append(Issue(
    #         id="custom-multiple-h1",
    #         description="Page should ideally have only one H1 heading.",
    #         help="While not strictly a WCAG failure, having more than one H1 can confuse screen reader users who expect a single primary heading for page navigation.",
    #         severity="moderate",
    #         nodes=[IssueNode(html=str(h1), target=["h1"]) for h1 in h1_tags],
    #         ai_suggestions=AiSuggestion(
    #             short_fix="Consolidate H1s or use other heading levels.",
    #             detailed_fix="Review your page's content structure. If multiple H1s are used, consider if secondary sections should be `<h2>` or `<h3>` instead. Reserve `<h1>` for the most important heading on the page."
    #         )
    #     ))

    # Rule 2: Check for skipped heading levels (e.g., H1 -> H3 without H2)
    # This checks for direct jumps in heading levels (e.g., h1 to h3, h2 to h4).
    # A proper check would traverse the DOM tree, but this simpler version checks for missing levels in the set of all found headings.

    all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    found_levels = set()
    for heading in all_headings:
        level = int(heading.name[1]) # Extracts the number from 'h1', 'h2', etc.
        found_levels.add(level)

    # Convert set to sorted list for easier iteration
    sorted_found_levels = sorted(list(found_levels))

    for i in range(len(sorted_found_levels) - 1):
        current_level = sorted_found_levels[i]
        next_level = sorted_found_levels[i+1]
        
        # If the next level is more than 1 greater than the current level, a skip occurred.
        # E.g., current_level=1 (H1), next_level=3 (H3) => 3 - 1 > 1.
        if next_level - current_level > 1:
            skipped_level = current_level + 1
            issues.append(Issue(
                id=f"custom-skipped-heading-level-h{skipped_level}",
                description=f"Skipped heading level: H{skipped_level} is missing between H{current_level} and H{next_level}.",
                help="Heading levels should follow a logical, hierarchical order. Do not skip levels (e.g., go from H1 directly to H3). This creates confusion for screen reader users navigating by headings, impairing content comprehension.",
                severity="moderate",
                nodes=[
                    # Provide context by including the HTML of the current and next heading if possible
                    IssueNode(html=str(soup.find(f'h{current_level}')), target=[f'h{current_level}']),
                    IssueNode(html=str(soup.find(f'h{next_level}')), target=[f'h{next_level}'])
                ],
                ai_suggestions=AiSuggestion(
                    short_fix=f"Ensure consecutive heading levels (e.g., H{current_level} then H{current_level + 1}).",
                    detailed_fix=f"Review the heading structure around the skipped H{skipped_level} level. If content under an `H{next_level}` logically follows an `H{current_level}`, consider if an intermediate `H{current_level + 1}` heading is needed to maintain hierarchy. Alternatively, adjust the heading levels to ensure no levels are skipped (e.g., change `H{next_level}` to `H{current_level + 1}`)."
                )
            ))
            # Break after finding one skipped level to avoid redundant reporting for the same skip scenario,
            # or continue if you want to report all instances.
            # For simplicity, we'll break for now.
            break

    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/headings.py locally ---")

    # Test 1: Missing H1
    html_no_h1 = "<html><body><h2>Subtitle</h2><p>Content</p></body></html>"
    issues_no_h1 = check_heading_structure(html_no_h1)
    print(f"\nTest 1 (No H1): Found {len(issues_no_h1)} issues.")
    for issue in issues_no_h1:
        print(issue.json(indent=2))

    # Test 2: Correct structure
    html_good_headings = "<html><body><h1>Main Title</h1><h2>Subtitle 1</h2><h3>Sub-subtitle</h3><h2>Subtitle 2</h2></body></html>"
    issues_good = check_heading_structure(html_good_headings)
    print(f"\nTest 2 (Good Headings): Found {len(issues_good)} issues.")
    for issue in issues_good:
        print(issue.json(indent=2))

    # Test 3: Skipped level (H1 -> H3)
    html_skipped_h2 = "<html><body><h1>Main Title</h1><h3>Sub-subtitle</h3></body></html>"
    issues_skipped = check_heading_structure(html_skipped_h2)
    print(f"\nTest 3 (Skipped H2): Found {len(issues_skipped)} issues.")
    for issue in issues_skipped:
        print(issue.json(indent=2))
    
    # Test 4: H2 without H1 (will trigger missing H1, but also skipped level if there's an H3 later)
    html_h2_no_h1 = "<html><body><h2>Just an H2</h2><h3>A sub-section</h3></body></html>"
    issues_h2_no_h1 = check_heading_structure(html_h2_no_h1)
    print(f"\nTest 4 (H2 without H1 + H3): Found {len(issues_h2_no_h1)} issues.")
    for issue in issues_h2_no_h1:
        print(issue.json(indent=2))
    
    # Test 5: Multiple skipped levels (H1 -> H4)
    html_skipped_multiple = "<html><body><h1>Main Heading</h1><h4>Section Detail</h4></body></html>"
    issues_skipped_multiple = check_heading_structure(html_skipped_multiple)
    print(f"\nTest 5 (H1 -> H4): Found {len(issues_skipped_multiple)} issues.")
    for issue in issues_skipped_multiple:
        print(issue.json(indent=2))
