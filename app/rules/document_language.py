# backend/app/rules/document_language.py

from bs4 import BeautifulSoup
from typing import List
from ..schemas import Issue, IssueNode, AiSuggestion

def check_document_language(html_content: str) -> List[Issue]:
    """
    Checks if the <html> element has a valid 'lang' attribute.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    html_tag = soup.find('html')

    if not html_tag:
        # This is a very rare case for valid HTML, but handle defensively
        issues.append(Issue(
            id="custom-missing-html-tag",
            description="No <html> tag found in the document.",
            help="The document must have an <html> tag as the root element. This is fundamental for proper parsing and accessibility.",
            severity="critical",
            nodes=[IssueNode(html=html_content[:100], target=["document"])], # Show start of doc
            ai_suggestions=AiSuggestion(
                short_fix="Add an <html> tag as the root element of the HTML document.",
                detailed_fix="Ensure your HTML document starts with `<!DOCTYPE html><html lang=\"en\">...</html>`. The `<html>` tag is the root element and is essential for browser rendering and accessibility tools."
            )
        ))
        return issues # No need to proceed if <html> tag is missing

    # Check if 'lang' attribute is missing or empty
    lang_attribute = html_tag.get('lang')
    if not lang_attribute or not lang_attribute.strip():
        issues.append(Issue(
            id="custom-missing-lang-attribute",
            description="The <html> element is missing a 'lang' attribute or its value is empty.",
            help="The 'lang' attribute on the <html> tag declares the primary human language of the document. This is crucial for screen readers to pronounce content correctly and for search engines.",
            severity="critical",
            nodes=[IssueNode(html=str(html_tag), target=["html"])],
            ai_suggestions=AiSuggestion(
                short_fix="Add `lang=\"en\"` (or appropriate language code) to the <html> tag.",
                detailed_fix="Add the `lang` attribute to your `<html>` tag, specifying the primary language of the document using a valid ISO 639-1 language code (e.g., `en` for English, `es` for Spanish, `fr` for French). For example: `<html lang=\"en\">`. This helps assistive technologies to render content correctly and improves translation services."
            )
        ))
    # TODO: Could add a more advanced check for valid language codes, but that's complex.

    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/document_language.py locally ---")

    # Test 1: Missing lang attribute (bad)
    html_no_lang = "<html><body><p>Hello world.</p></body></html>"
    issues_no_lang = check_document_language(html_no_lang)
    print(f"\nTest 1 (No Lang): Found {len(issues_no_lang)} issues.")
    for issue in issues_no_lang:
        print(issue.json(indent=2))

    # Test 2: Empty lang attribute (bad)
    html_empty_lang = "<html lang=\"\"><body><p>Hello world.</p></body></html>"
    issues_empty_lang = check_document_language(html_empty_lang)
    print(f"\nTest 2 (Empty Lang): Found {len(issues_empty_lang)} issues.")
    for issue in issues_empty_lang:
        print(issue.json(indent=2))

    # Test 3: Correct lang attribute (good)
    html_good_lang = "<html lang=\"en\"><body><p>Hello world.</p></body></html>"
    issues_good_lang = check_document_language(html_good_lang)
    print(f"\nTest 3 (Good Lang): Found {len(issues_good_lang)} issues.")
    for issue in issues_good_lang:
        print(issue.json(indent=2))

    # Test 4: Lang attribute with whitespace (bad)
    html_whitespace_lang = "<html lang=\"  \"><body><p>Hello world.</p></body></html>"
    issues_whitespace_lang = check_document_language(html_whitespace_lang)
    print(f"\nTest 4 (Whitespace Lang): Found {len(issues_whitespace_lang)} issues.")
    for issue in issues_whitespace_lang:
        print(issue.json(indent=2))
