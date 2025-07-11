# backend/app/services/ai_helper.py

import os
from dotenv import load_dotenv
import json
import httpx # Using httpx for async HTTP requests
import logging # Import logging
from typing import Dict, Optional, Any

# Configure logging for this module
logger = logging.getLogger("accessibility_analyzer_backend.services.ai_helper")

# Load environment variables from .env file (if running locally).
# This needs to be called at the start of your application where env vars are accessed.
# In a full FastAPI app, it might be in main.py or a config module, but for now, here is fine.
load_dotenv()

# Retrieve the Gemini API key from environment variables.
# This key should be set in your .env file at the backend root.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# The endpoint for the Gemini 2.0 Flash model.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def extract_json_from_text(text: str) -> Optional[str]:
    """
    Attempts to extract a JSON string from a text, handling cases where it's wrapped
    in markdown code blocks.
    """
    if text.strip().startswith('{') and text.strip().endswith('}'):
        return text.strip()
    
    # Try to find JSON within a markdown code block
    # This regex is simplified; for more complex cases, a proper JSON parser might be needed
    # or more sophisticated regex.
    # Pattern: ```json\n (.*) \n```
    start_tag = "```json\n"
    end_tag = "\n```"
    if start_tag in text and end_tag in text:
        start_index = text.find(start_tag) + len(start_tag)
        end_index = text.find(end_tag, start_index)
        if start_index != -1 and end_index != -1:
            return text[start_index:end_index].strip()
    return None


async def get_ai_suggestions(issue_description: str, issue_help: str, issue_html_node: str) -> Dict[str, str]:
    """
    Calls the Gemini API to generate a concise "short fix" and a "detailed fix" suggestion
    for a given accessibility issue.

    Args:
        issue_description (str): A brief description of the accessibility issue (e.g., "Image has no alt text").
        issue_help (str): A more detailed explanation of why the issue matters and how to generally fix it.
        issue_html_node (str): The HTML snippet of the specific element causing the issue, for context.

    Returns:
        Dict[str, str]: A dictionary with two keys:
                            - 'short_fix': A concise summary of the fix.
                            - 'detailed_fix': A more elaborate step-by-step or technical solution.
                            Returns placeholder messages if the API key is missing or the API call fails.
    """
    # Check if the API key is available before making the request.
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY environment variable is not set. AI suggestions will not be generated.")
        return {
            "short_fix": "AI suggestions not available (API key missing).",
            "detailed_fix": "Please set the GEMINI_API_KEY environment variable in your .env file."
        }

    # Construct the prompt for the Gemini model.
    # The prompt guides the AI to act as an accessibility expert and to provide
    # solutions in a specific format (JSON).
    prompt = f"""
    You are an expert web accessibility consultant. Provide a concise "short fix" and a detailed "detailed fix" for the following accessibility issue. The tone should be professional, helpful, and action-oriented.

    **Accessibility Issue:** {issue_description}
    **Help Text:** {issue_help}
    **Problematic HTML Element:** `{issue_html_node}`

    Provide the response in JSON format with two keys: "short_fix" and "detailed_fix".
    Ensure the JSON is perfectly valid and ready for direct parsing.
    Example:
    {{
        "short_fix": "Add alt text to the image.",
        "detailed_fix": "For the image `<img>`, add an `alt` attribute that describes its content or purpose. If purely decorative, use `alt=\"\"`."
    }}
    """

    # Define the payload for the Gemini API request.
    # We specify `responseMimeType` and `responseSchema` to encourage the model
    # to return a structured JSON response, making parsing more reliable.
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json", # Tells Gemini to aim for JSON output
            "responseSchema": { # Defines the expected JSON structure
                "type": "OBJECT",
                "properties": {
                    "short_fix": {"type": "STRING"},
                    "detailed_fix": {"type": "STRING"}
                },
                "required": ["short_fix", "detailed_fix"]
            }
        }
    }

    # Set HTTP headers for the request.
    headers = {
        'Content-Type': 'application/json',
    }
    # Append the API key as a query parameter to the URL.
    request_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        # Use httpx.AsyncClient for asynchronous HTTP requests.
        # This is important for a FastAPI app to remain non-blocking.
        async with httpx.AsyncClient() as client:
            response = await client.post(request_url, headers=headers, json=payload, timeout=60.0) # Increased timeout
            response.raise_for_status() # Raise an exception for bad HTTP status codes (4xx or 5xx)
            
            result = response.json()
            logger.debug(f"Gemini raw response: {json.dumps(result, indent=2)}") # Log the raw response

            # Navigate through the nested structure of the Gemini API response
            if result and 'candidates' in result and result['candidates']:
                first_candidate = result['candidates'][0]
                if 'content' in first_candidate and 'parts' in first_candidate['content']:
                    for part in first_candidate['content']['parts']:
                        if 'text' in part:
                            extracted_json_str = extract_json_from_text(part['text'])
                            if extracted_json_str:
                                try:
                                    # The model returns the JSON object as a string, so we need to parse it again.
                                    ai_suggestions = json.loads(extracted_json_str)
                                    # Validate that the expected keys are present in the parsed JSON.
                                    if "short_fix" in ai_suggestions and "detailed_fix" in ai_suggestions:
                                        logger.info("Successfully received and parsed AI suggestions from Gemini.")
                                        return ai_suggestions
                                    else:
                                        logger.warning(f"Gemini response missing expected keys: {ai_suggestions}")
                                        return {
                                            "short_fix": "AI suggestions incomplete.",
                                            "detailed_fix": "Gemini API returned an incomplete response."
                                        }
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse Gemini response text as valid JSON: {extracted_json_str}")
                                    return {
                                        "short_fix": "AI suggestions parsing error.",
                                        "detailed_fix": "Gemini API returned unparseable JSON."
                                    }
                            else:
                                logger.warning(f"Could not extract JSON from Gemini response text: {part['text']}")
                                return {
                                    "short_fix": "AI suggestions extraction error.",
                                    "detailed_fix": "Gemini API response format was not as expected."
                                }
            logger.warning("Gemini API response structure unexpected or empty.")
            return {
                "short_fix": "AI suggestions generation failed.",
                "detailed_fix": "Gemini API did not return expected content structure."
            }

    except httpx.RequestError as e:
        # Handle network-related errors during the HTTP request.
        logger.error(f"HTTPX request error during Gemini API call: {e}", exc_info=True)
        return {
            "short_fix": "AI suggestion API request error.",
            "detailed_fix": f"Network or API connectivity issue: {e}"
        }
    except httpx.HTTPStatusError as e:
        # Handle HTTP status errors returned by the Gemini API.
        logger.error(f"HTTP error during Gemini API call: {e.response.status_code} - {e.response.text}", exc_info=True)
        return {
            "short_fix": "AI suggestion API returned error status.",
            "detailed_fix": f"Gemini API returned an error: Status {e.response.status_code}, Detail: {e.response.text}"
        }
    except Exception as e:
        # Catch any other unexpected errors.
        logger.error(f"An unexpected error occurred during Gemini API call: {e}", exc_info=True)
        return {
            "short_fix": "AI suggestion internal error.",
            "detailed_fix": f"An unexpected error occurred during AI suggestion generation: {e}"
        }

# This __main__ block is for local testing of this specific helper file.
# It will not run when the module is imported by FastAPI.
if __name__ == "__main__":
    import asyncio
    import sys

    # Basic console logging setup for local testing
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set httpx logging to warning to avoid verbose output from its internals
    logging.getLogger("httpx").setLevel(logging.WARNING)

    async def test_ai_suggestions_local():
        logger.info("--- Testing backend/app/services/ai_helper.py locally ---")
        
        # Ensure GEMINI_API_KEY is set in your .env file or environment for local testing.
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set. Please set it in your .env file or as an environment variable.")
            return

        # Test case 1: Missing alt text issue
        test_issue_description_1 = "Image element has no `alt` attribute"
        test_issue_help_1 = "Assistive technologies cannot convey the purpose of an image if it has no text alternative. Make sure the alt text concisely describes the content or function of the image."
        test_issue_html_1 = "<img src='logo.png'>"
        logger.info(f"\nRequesting AI suggestions for: '{test_issue_description_1}' (HTML: `{test_issue_html_1}`)")
        suggestions_1 = await get_ai_suggestions(test_issue_description_1, test_issue_help_1, test_issue_html_1)
        logger.info("AI Suggestions (Test 1):")
        logger.info(json.dumps(suggestions_1, indent=2))

        # Test case 2: Insufficient color contrast issue
        test_issue_description_2 = "Insufficient color contrast"
        test_issue_help_2 = "Text and background must have a sufficient contrast ratio (4.5:1 for normal text, 3:1 for large text) to be readable for users with visual impairments."
        test_issue_html_2 = "<p style='color: #FFF; background-color: #DDD;'>Important notice</p>"
        logger.info(f"\nRequesting AI suggestions for: '{test_issue_description_2}' (HTML: `{test_issue_html_2}`)")
        suggestions_2 = await get_ai_suggestions(test_issue_description_2, test_issue_help_2, test_issue_html_2)
        logger.info("AI Suggestions (Test 2):")
        logger.info(json.dumps(suggestions_2, indent=2))

        # Test case 3: Empty node for AI context
        test_issue_description_3 = "Page has no main landmark"
        test_issue_help_3 = "Assistive technologies use landmarks to navigate the page. Ensure there is one <main> element."
        test_issue_html_3 = "" # No specific node might be available for page-level issues
        logger.info(f"\nRequesting AI suggestions for: '{test_issue_description_3}' (HTML: `{test_issue_html_3}`)")
        suggestions_3 = await get_ai_suggestions(test_issue_description_3, test_issue_help_3, test_issue_html_3)
        logger.info("AI Suggestions (Test 3):")
        logger.info(json.dumps(suggestions_3, indent=2))

    # Run the local test function
    asyncio.run(test_ai_suggestions_local())