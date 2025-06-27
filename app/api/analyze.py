# backend/app/api/analyze.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import HttpUrl
from typing import List
import datetime
import asyncio # Required for asyncio.gather
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import os # For environment variables
from dotenv import load_dotenv # For loading .env file
from bs4 import BeautifulSoup # Used for extracting page title

# Load environment variables from .env file
load_dotenv()

# Import your schemas (data models)
from ..schemas import AnalysisRequest, AnalysisResult, Issue, AnalysisSummary, AiSuggestion

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

router = APIRouter()

# --- MongoDB Connection ---
# It's best practice to get MongoDB URI from environment variables for security and flexibility
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "accessibility_analyzer_db")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "analysis_results")

# Initialize MongoDB client
client = None # Initialize client to None
analysis_collection = None # Initialize collection to None

try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    analysis_collection = db[MONGO_COLLECTION_NAME]
    # Optional: Ping the database to check connection immediately
    client.admin.command('ping')
    print(f"Successfully connected to MongoDB: {MONGO_DB_NAME}")
    # Create a unique index on the 'url' field for faster lookups
    analysis_collection.create_index("url", unique=True, background=True)
    print("MongoDB index on 'url' created/ensured.")
except ConnectionFailure as e:
    print(f"Could not connect to MongoDB at {MONGO_URI}: {e}")
    # In a real application, you might want to exit or log a critical error.
    # For now, we'll let the app start but analysis will fail if DB is used.
    analysis_collection = None # Set to None to prevent usage if connection fails
except OperationFailure as e:
    print(f"MongoDB operation error (e.g., index creation issue): {e}")
    analysis_collection = None
except Exception as e:
    print(f"An unexpected error occurred during MongoDB connection: {e}")
    analysis_collection = None


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_url(request: AnalysisRequest = Body(...)):
    """
    Analyzes a given URL for accessibility issues.
    Checks MongoDB cache first. If a recent analysis exists, returns it immediately.
    Otherwise, performs a new analysis, generates AI suggestions, and caches the result.
    """
    url = request.url
    print(f"Received request to analyze URL: {url}")

    # Corrected: Use 'is not None' to check if analysis_collection was successfully initialized
    if analysis_collection is not None:
        # Check cache for existing result for this URL
        # We store URL as string in DB, so convert HttpUrl to string for query
        cached_result_doc = analysis_collection.find_one({"url": str(url)})
        
        if cached_result_doc:
            # You might want to add a timestamp check here to determine if the cache is "fresh"
            # For example: if (datetime.datetime.now(datetime.timezone.utc) - cached_result_doc['timestamp']).days < 7:
            print(f"Returning cached analysis for URL: {url}")
            
            # MongoDB's _id field needs to be handled for Pydantic's validation
            # Convert ObjectId to string for Pydantic processing
            if '_id' in cached_result_doc:
                cached_result_doc['id'] = str(cached_result_doc['_id'])
                del cached_result_doc['_id'] # Remove original _id to avoid conflict with 'id' alias
            
            # Ensure HttpUrl is passed as string to Pydantic if it was stored as string
            cached_result_doc['url'] = str(cached_result_doc['url']) 
            
            # Ensure summary.score is an int if it was stored as int, or handle conversion
            if 'summary' in cached_result_doc and 'score' in cached_result_doc['summary']:
                cached_result_doc['summary']['score'] = int(cached_result_doc['summary']['score'])

            try:
                # Convert BSON document back to Pydantic model
                return AnalysisResult(**cached_result_doc)
            except Exception as e:
                print(f"Error converting cached document to Pydantic model: {e}. Re-analyzing.")
                # Fall through to re-analysis if cached data is malformed
        else:
            print(f"No cached analysis found for URL: {url}. Performing new analysis.")
    else:
        print("MongoDB connection not established. Skipping cache lookup and proceeding with new analysis.")

    driver = None
    issues: List[Issue] = []
    # Initialize summary with zero counts before analysis starts, and score
    summary = AnalysisSummary(total_issues=0, critical=0, moderate=0, minor=0, score=100)
    page_html_content = ""
    page_title = "N/A" # Initialize page_title to N/A

    try:
        # Step 1: Initialize headless browser
        driver = get_webdriver("chrome")
        
        # Step 2: Navigate to the URL and get page HTML
        driver.get(str(url)) 
        page_html_content = driver.page_source 
        
        # Get page title (useful for the report heading)
        try:
            # from bs4 import BeautifulSoup # Already imported at the top
            soup = BeautifulSoup(page_html_content, 'lxml')
            page_title_tag = soup.find('title')
            if page_title_tag and page_title_tag.string:
                page_title = page_title_tag.string.strip()
        except Exception as title_e:
            print(f"Could not extract page title: {title_e}")


        # Step 3: Run Axe-core accessibility scan
        axe_violations_raw = run_axe_scan(driver)
        for viol in axe_violations_raw:
            issues.append(Issue(**viol)) 

        # Step 4: Run Custom BeautifulSoup rules
        issues.extend(check_alt_text(page_html_content))          
        issues.extend(check_heading_structure(page_html_content)) 
        issues.extend(check_form_labels(page_html_content))       
        issues.extend(check_color_contrast(page_html_content))    
        issues.extend(check_empty_interactive_elements(page_html_content))
        issues.extend(check_document_language(page_html_content))
        issues.extend(check_descriptive_link_text(page_html_content))
        issues.extend(check_media_captions(page_html_content))

        # Step 5: Generate AI suggestions for each detected issue
        tasks = []
        for issue in issues:
            problematic_html = issue.nodes[0].html if issue.nodes else ""
            tasks.append(get_ai_suggestions(issue.description, issue.help, problematic_html))
        
        ai_suggestions_results = await asyncio.gather(*tasks)

        for i, suggestion_data in enumerate(ai_suggestions_results):
            issues[i].ai_suggestions = AiSuggestion(**suggestion_data)


        # Step 6: Calculate the comprehensive analysis summary and accessibility score
        summary.total_issues = len(issues)
        
        critical_deduction = 0
        moderate_deduction = 0
        minor_deduction = 0

        CRITICAL_WEIGHT = 5
        MODERATE_WEIGHT = 2
        MINOR_WEIGHT = 1

        for issue in issues:
            if issue.severity == "critical":
                summary.critical += 1
                critical_deduction += CRITICAL_WEIGHT
            elif issue.severity in ["serious", "moderate"]: 
                summary.moderate += 1
                moderate_deduction += MODERATE_WEIGHT
            elif issue.severity == "minor":
                summary.minor += 1
                minor_deduction += MINOR_WEIGHT

        calculated_score = 100 - (critical_deduction + moderate_deduction + minor_deduction)
        summary.score = max(0, calculated_score)

        # Final result to return
        final_result = AnalysisResult(
            url=url,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            summary=summary,
            issues=issues,
            page_title=page_title # Include the fetched page title
        )

        # Step 7: Cache the new analysis result in MongoDB
        # Corrected: Use 'is not None' to check if analysis_collection was successfully initialized
        if analysis_collection is not None:
            try:
                # Convert Pydantic model to dictionary for MongoDB insertion
                # Use by_alias=True to handle '_id' alias correctly if present in model (for future reads)
                # Ensure HttpUrl is converted to string for MongoDB
                doc_to_save = final_result.model_dump(by_alias=True)
                
                # If an ID was assigned (from a new object or existing), convert PyObjectId to string for MongoDB
                if '_id' in doc_to_save and doc_to_save['_id'] is not None:
                    # PyObjectId itself will convert to string during model_dump if configured.
                    # We just need to make sure _id is the key used in MongoDB.
                    pass # Handled by Pydantic's alias and json_encoders
                
                doc_to_save['url'] = str(final_result.url) # Ensure URL is stored as string
                
                # upsert=True will insert if url doesn't exist, or update if it does.
                analysis_collection.update_one(
                    {"url": str(url)}, # Query to find existing document by URL
                    {"$set": doc_to_save}, # The data to set/update
                    upsert=True # Insert if no matching document is found
                )
                print(f"Analysis result for {url} cached successfully.")
            except Exception as db_e:
                print(f"Error saving analysis result to MongoDB: {db_e}")

        return final_result

    except Exception as e:
        print(f"Error during analysis of {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if driver:
            driver.quit()
