# backend/app/rules/contrast.py

from bs4 import BeautifulSoup
import re
from typing import List, Tuple, Optional
from ..schemas import Issue, IssueNode, AiSuggestion

# --- Helper Functions for Color Conversion and Contrast Calculation ---
# These functions are simplified. A robust solution would use a dedicated library
# like 'colour' or 'colormath' for accurate color space conversions and contrast.

def hex_to_rgb(hex_color: str) -> Optional[Tuple[int, int, int]]:
    """Converts a hex color string (e.g., #RRGGBB or #RGB) to an RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color]) # Expand #RGB to #RRGGBB
    
    if len(hex_color) == 6:
        try:
            return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except ValueError:
            return None
    return None

def get_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculates the relative luminance of an RGB color, per WCAG."""
    R, G, B = [x / 255.0 for x in rgb]
    Rs, Gs, Bs = [], [], []

    for color in [R, G, B]:
        if color <= 0.03928:
            c_srgb = color / 12.92
        else:
            c_srgb = ((color + 0.055) / 1.055) ** 2.4
        Rs.append(c_srgb)
    
    # L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    return 0.2126 * Rs[0] + 0.7152 * Rs[1] + 0.0722 * Rs[2]

def get_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculates the contrast ratio between two RGB colors."""
    L1 = get_luminance(rgb1)
    L2 = get_luminance(rgb2)
    
    # Ensure L1 is the lighter of the two
    if L2 > L1:
        L1, L2 = L2, L1
        
    return (L1 + 0.05) / (L2 + 0.05)

# --- Main Rule Function ---

def check_color_contrast(html_content: str) -> List[Issue]:
    """
    Performs a basic check for color contrast based on inline styles and
    <style> tags. Note: This rule is limited as it does not parse external CSS
    or computed styles, which are crucial for accurate contrast checking.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    issues: List[Issue] = []

    # Find elements with potential text and background colors
    elements = soup.find_all(lambda tag: tag.name in ['p', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'li', 'td', 'th', 'label'] and tag.get_text(strip=True))

    for element in elements:
        # Skip if the element's text content is empty or contains only whitespace
        if not element.get_text(strip=True):
            continue
        
        # Simplified approach: Check inline styles first
        style = element.get('style')
        text_color_hex = None
        bg_color_hex = None

        if style:
            text_match = re.search(r'color:\s*#([0-9a-fA-F]{3}){1,2}', style)
            bg_match = re.search(r'background-color:\s*#([0-9a-fA-F]{3}){1,2}', style)
            
            if text_match:
                text_color_hex = text_match.group(0).split(':')[1].strip()
            if bg_match:
                bg_color_hex = bg_match.group(0).split(':')[1].strip()
        
        # For a more comprehensive check, you'd also need to:
        # 1. Parse <style> tags and apply rules based on selectors (complex).
        # 2. Consider default browser styles.
        # 3. Handle rgba, rgb, named colors, HSL, etc.
        # 4. Get *computed* styles which reflects all inherited and applied CSS.

        # For this simplified version, if we can't find both colors, we skip.
        if not (text_color_hex and bg_color_hex):
            continue
        
        text_rgb = hex_to_rgb(text_color_hex)
        bg_rgb = hex_to_rgb(bg_color_hex)

        if not (text_rgb and bg_rgb):
            continue # Could not parse colors

        contrast = get_contrast_ratio(text_rgb, bg_rgb)
        
        # WCAG 2.1 AA requirements:
        # Normal text: 4.5:1
        # Large text (18pt/24px or 14pt/18.66px bold): 3:1
        # Since we can't reliably detect "large text" from static HTML, we use 4.5:1 for all.
        required_ratio = 4.5

        if contrast < required_ratio:
            issue_html = str(element)
            issues.append(Issue(
                id="custom-color-contrast-low",
                description=f"Low color contrast: The contrast ratio is {contrast:.2f}:1, but requires {required_ratio}:1.",
                help=f"Text and background colors must have a sufficient contrast ratio ({required_ratio}:1 for normal text) to be readable for users with visual impairments and in varying lighting conditions. Without sufficient contrast, text can be difficult or impossible for some users to read.",
                severity="critical", # Contrast issues are often critical
                nodes=[IssueNode(html=issue_html, target=[element.name])],
                ai_suggestions=AiSuggestion(
                    short_fix="Increase the contrast between text and background colors.",
                    detailed_fix=f"For the element: `{issue_html}`, modify the `color` and/or `background-color` to achieve a contrast ratio of at least {required_ratio}:1. Use a color contrast checker tool (e.g., WebAIM Contrast Checker) to find suitable color combinations. Consider making the text darker or the background lighter (or vice-versa) to improve readability. Ensure this applies to all states (hover, focus, active) if dynamic styles are used."
                )
            ))
    
    return issues

if __name__ == "__main__":
    print("--- Testing backend/app/rules/contrast.py locally ---")

    # Test 1: Good contrast (white on black)
    html_good_contrast = """
    <html><body>
        <p style="color:#FFF; background-color:#000;">This text has good contrast.</p>
    </body></html>
    """
    issues_good = check_color_contrast(html_good_contrast)
    print(f"\nTest 1 (Good Contrast): Found {len(issues_good)} issues.")
    for issue in issues_good:
        print(issue.json(indent=2))

    # Test 2: Bad contrast (light grey on white)
    html_bad_contrast = """
    <html><body>
        <span style="color:#AAA; background-color:#FFF;">This text has poor contrast.</span>
        <div style="color:#777; background-color:#DDD;">Another example of low contrast.</div>
    </body></html>
    """
    issues_bad = check_color_contrast(html_bad_contrast)
    print(f"\nTest 2 (Bad Contrast): Found {len(issues_bad)} issues.")
    for issue in issues_bad:
        print(issue.json(indent=2))

    # Test 3: No inline styles (should find no issues with this simple rule)
    html_no_styles = "<html><body><h1>Page Title</h1><p>Some content.</p></body></html>"
    issues_no_styles = check_color_contrast(html_no_styles)
    print(f"\nTest 3 (No Inline Styles): Found {len(issues_no_styles)} issues.")
    for issue in issues_no_styles:
        print(issue.json(indent=2))
    
    # Test 4: Mixed hex format
    html_mixed_hex = """
    <html><body>
        <p style="color:#ABC; background-color:#123456;">Mixed hex format.</p>
    </body></html>
    """
    issues_mixed_hex = check_color_contrast(html_mixed_hex)
    print(f"\nTest 4 (Mixed Hex): Found {len(issues_mixed_hex)} issues.")
    for issue in issues_mixed_hex:
        print(issue.json(indent=2))
