# backend/app/rules/labels.py

from bs4 import BeautifulSoup
from typing import List
from ..schemas import Issue, IssueNode, AiSuggestion

def check_form_labels(html_content: str) -> List[Issue]:
    """
    Checks for form input fields (input, textarea, select) that are missing
    proper associated labels or aria-label/aria-labelledby attributes.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Find all relevant form input elements
    form_elements = soup.find_all(['input', 'textarea', 'select'])

    for element in form_elements:
        # Exclude specific input types that don't typically need a visible label
        # or are handled differently (e.g., submit buttons, hidden fields).
        input_type = element.get('type', '').lower()
        if input_type in ['hidden', 'submit', 'reset', 'button', 'image']:
            continue

        # Check for associated <label> tag using 'for' attribute
        has_label_for = False
        element_id = element.get('id')
        if element_id:
            # Find if any <label> tag has a 'for' attribute matching this element's ID
            if soup.find('label', {'for': element_id}):
                has_label_for = True

        # Check for aria-label or aria-labelledby attributes
        has_aria_label = bool(element.get('aria-label') or element.get('aria-labelledby'))

        # Check for placeholder text (often misused as a label, which is not accessible)
        has_placeholder = bool(element.get('placeholder'))

        # If no accessible name is provided, raise an issue
        if not has_label_for and not has_aria_label:
            issue_html = str(element)

            # Refine description/help based on placeholder presence
            if has_placeholder:
                description = "Form field has a placeholder but no proper accessible label."
                help_text = "Placeholder text disappears on input and is not announced by all screen readers. Ensure all form fields have a visible `<label>` element associated using `for`/`id` or an `aria-label`/`aria-labelledby` attribute for accessibility."
                short_fix = "Add a `<label>` or `aria-label` to the form field."
                detailed_fix = f"For the element: `{issue_html}`, add a `<label>` element with a `for` attribute matching the input's `id` (e.g., `<label for=\"input_id\">Your Name</label><input id=\"input_id\" type=\"text\">`). Alternatively, use `aria-label=\"Descriptive Text\"` directly on the input element, or `aria-labelledby=\"id_of_label_text\"` if the label text is elsewhere on the page. **Do not rely solely on placeholder text for labeling.**"
            else:
                description = "Form field is missing an accessible label."
                help_text = "All form input elements must have an associated accessible name to be understandable by screen readers and other assistive technologies. This is typically done with a `<label>` element."
                short_fix = "Add a `<label>` or `aria-label` to the form field."
                detailed_fix = f"For the element: `{issue_html}`, add a `<label>` element with a `for` attribute matching the input's `id` (e.g., `<label for=\"input_id\">Your Name</label><input id=\"input_id\" type=\"text\">`). Alternatively, use `aria-label=\"Descriptive Text\"` directly on the input element, or `aria-labelledby=\"id_of_label_text\"` if the label text is elsewhere on the page."

            issues.append(Issue(
                id="custom-missing-form-label",
                description=description,
                help=help_text,
                severity="critical", # Missing labels are critical for usability
                nodes=[IssueNode(html=issue_html, target=[element.name])],
                ai_suggestions=AiSuggestion(
                    short_fix=short_fix,
                    detailed_fix=detailed_fix
                )
            ))
    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/labels.py locally ---")

    # Test 1: Input with no label or aria-label (bad)
    html_no_label = "<html><body><input type='text' id='username'></body></html>"
    issues_no_label = check_form_labels(html_no_label)
    print(f"\nTest 1 (No Label): Found {len(issues_no_label)} issues.")
    for issue in issues_no_label:
        print(issue.json(indent=2))

    # Test 2: Input with associated label (good)
    html_good_label = "<html><body><label for='email'>Email:</label><input type='email' id='email'></body></html>"
    issues_good_label = check_form_labels(html_good_label)
    print(f"\nTest 2 (Good Label): Found {len(issues_good_label)} issues.")
    for issue in issues_good_label:
        print(issue.json(indent=2))

    # Test 3: Input with aria-label (good)
    html_aria_label = "<html><body><input type='password' aria-label='Password'></body></html>"
    issues_aria_label = check_form_labels(html_aria_label)
    print(f"\nTest 3 (Aria Label): Found {len(issues_aria_label)} issues.")
    for issue in issues_aria_label:
        print(issue.json(indent=2))

    # Test 4: Input with placeholder but no proper label (bad)
    html_placeholder_only = "<html><body><input type='search' id='search' placeholder='Search...'></body></html>"
    issues_placeholder = check_form_labels(html_placeholder_only)
    print(f"\nTest 4 (Placeholder Only): Found {len(issues_placeholder)} issues.")
    for issue in issues_placeholder:
        print(issue.json(indent=2))

    # Test 5: Hidden input (should be ignored)
    html_hidden_input = "<html><body><input type='hidden' name='csrf' value='token'></body></html>"
    issues_hidden = check_form_labels(html_hidden_input)
    print(f"\nTest 5 (Hidden Input): Found {len(issues_hidden)} issues.")
    for issue in issues_hidden:
        print(issue.json(indent=2))