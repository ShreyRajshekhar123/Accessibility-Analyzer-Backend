# backend/app/rules/empty_interactive.py

from bs4 import BeautifulSoup
from typing import List
from ..schemas import Issue, IssueNode, AiSuggestion

def check_empty_interactive_elements(html_content: str) -> List[Issue]:
    """
    Checks for <a> and <button> elements that are empty or contain only whitespace,
    and lack an accessible name via aria-label or aria-labelledby.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Find all <a> and <button> tags
    interactive_elements = soup.find_all(['a', 'button'])

    for element in interactive_elements:
        # Check for visible text content or accessible name attributes
        has_visible_text = bool(element.get_text(strip=True))
        has_aria_label = bool(element.get('aria-label') or element.get('aria-labelledby'))
        
        # If the element has no visible text AND no accessible ARIA label
        if not has_visible_text and not has_aria_label:
            element_type = element.name # 'a' or 'button'
            issue_html = str(element)
            
            # Determine short and detailed fixes based on element type
            if element_type == 'a':
                short_fix = "Add descriptive text or an `aria-label` to the link."
                detailed_fix = f"The link: `{issue_html}` is empty. Add meaningful, descriptive text between the `<a>` tags (e.g., `<a href=\"...\">Learn More about Product X</a>`). If the link contains an icon and no visible text, add an `aria-label` attribute describing its purpose (e.g., `<a href=\"...\" aria-label=\"View Profile\"><img src=\"profile.png\" alt=\"\"></a>`)."
            elif element_type == 'button':
                short_fix = "Add descriptive text or an `aria-label` to the button."
                detailed_fix = f"The button: `{issue_html}` is empty. Add meaningful, descriptive text between the `<button>` tags (e.g., `<button type=\"submit\">Submit Form</button>`). If the button contains only an icon, provide an `aria-label` attribute describing its action (e.g., `<button aria-label=\"Delete Item\"><span class=\"icon-trash\"></span></button>`)."
            else: # Fallback for unexpected types, though limited to a/button
                short_fix = f"Provide an accessible name for the {element_type} element."
                detailed_fix = f"The {element_type} element: `{issue_html}` is missing an accessible name. Ensure it has visible text content or an `aria-label` attribute to convey its purpose to assistive technologies."


            issues.append(Issue(
                id=f"custom-empty-{element_type}",
                description=f"Empty {element_type} element detected.",
                help=f"Interactive elements like {element_type} must have an accessible name (visible text, `aria-label`, or `aria-labelledby`) to inform screen reader users of their purpose. Empty {element_type} elements are skipped by screen readers or announced generically, making them unusable.",
                severity="critical", # Empty interactive elements are a major barrier
                nodes=[IssueNode(html=issue_html, target=[element_type])],
                ai_suggestions=AiSuggestion(
                    short_fix=short_fix,
                    detailed_fix=detailed_fix
                )
            ))
    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/empty_interactive.py locally ---")

    # Test 1: Empty link (bad)
    html_empty_link = "<html><body><a href=\"#\"></a></body></html>"
    issues_empty_link = check_empty_interactive_elements(html_empty_link)
    print(f"\nTest 1 (Empty Link): Found {len(issues_empty_link)} issues.")
    for issue in issues_empty_link:
        print(issue.json(indent=2))

    # Test 2: Empty button (bad)
    html_empty_button = "<html><body><button></button></body></html>"
    issues_empty_button = check_empty_interactive_elements(html_empty_button)
    print(f"\nTest 2 (Empty Button): Found {len(issues_empty_button)} issues.")
    for issue in issues_empty_button:
        print(issue.json(indent=2))

    # Test 3: Link with text (good)
    html_good_link = "<html><body><a href=\"#\">Click Me</a></body></html>"
    issues_good_link = check_empty_interactive_elements(html_good_link)
    print(f"\nTest 3 (Good Link): Found {len(issues_good_link)} issues.")
    for issue in issues_good_link:
        print(issue.json(indent=2))
    
    # Test 4: Button with aria-label (good)
    html_aria_button = "<html><body><button aria-label=\"Close dialog\"><span class=\"icon-x\"></span></button></body></html>"
    issues_aria_button = check_empty_interactive_elements(html_aria_button)
    print(f"\nTest 4 (Aria Label Button): Found {len(issues_aria_button)} issues.")
    for issue in issues_aria_button:
        print(issue.json(indent=2))

    # Test 5: Link with only whitespace (bad)
    html_whitespace_link = "<html><body><a href=\"#\">     </a></body></html>"
    issues_whitespace_link = check_empty_interactive_elements(html_whitespace_link)
    print(f"\nTest 5 (Whitespace Link): Found {len(issues_whitespace_link)} issues.")
    for issue in issues_whitespace_link:
        print(issue.json(indent=2))
