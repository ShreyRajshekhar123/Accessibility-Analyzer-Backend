# backend/app/api/analyze.py

from fastapi import APIRouter, HTTPException, Body, Depends, status
from pydantic import HttpUrl, ValidationError
import logging
import traceback
# from bson.errors import InvalidId # No longer needed here as report routes are moved

# --- Import your schemas (data models) ---
from ..schemas import AnalysisRequest, AnalysisResult # Only import schemas directly used by this endpoint

# --- Import the new modular components ---
from ..database.repository import AnalysisRepository
from ..core.analyzer import run_full_analysis
from ..core.result_processor import process_analysis_data

# --- IMPORTANT: Correct Import for Authentication Dependency ---
# This line ensures you import the actual callable function
from ..auth.auth_dependency import get_current_user_firebase

# --- FastAPI Router Definition ---
router = APIRouter()

# --- Logger for this module ---
logger = logging.getLogger("accessibility_analyzer_backend.api.analyze")

# --- Define the current_user_dependency using the imported function ---
current_user_dependency = Depends(get_current_user_firebase)


# --- Dependency for AnalysisRepository ---
async def get_analysis_repository() -> AnalysisRepository:
    """
    Dependency that provides an instance of AnalysisRepository.
    This ensures the repository is initialized *after* the MongoDB connection
    is established in the application's startup event.
    """
    return AnalysisRepository()


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=True
)
async def analyze_url(
    request: AnalysisRequest = Body(...),
    current_user: dict = current_user_dependency, # This uses the Depends(get_current_user_firebase)
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository)
):
    """
    Analyzes a given URL for accessibility issues.
    Checks MongoDB cache first. If a recent analysis exists, returns it immediately.
    Otherwise, performs a new analysis, generates AI suggestions, and caches the result.
    """
    url = request.url
    user_id = current_user["uid"]

    logger.info(f"API Request: POST /analyze | URL: {url} | User: {user_id}")

    try:
        # --- Cache Lookup ---
        # The repository's get_analysis_by_url_and_user handles the cache validity internally
        cached_result = await analysis_repo.get_analysis_by_url_and_user(url, user_id)
        if cached_result:
            logger.info(f"Cache Hit: Returning cached analysis for URL: {url} | User: {user_id} | Report ID: {cached_result.id}")
            return cached_result
        else:
            logger.info(f"Cache Miss: No cached analysis found for URL: {url} | User: {user_id}. Performing new analysis.")

        # --- Perform new analysis ---
        issues_list, page_html_content, page_title = await run_full_analysis(url)
        
        # --- Process analysis data into final AnalysisResult model ---
        final_result = process_analysis_data(url, user_id, issues_list, page_html_content, page_title)

        # --- Save/Update Report to MongoDB ---
        saved_result = await analysis_repo.save_analysis_result(final_result)
        logger.info(f"Analysis process completed successfully and saved for URL: {url} | User: {user_id} | Report ID: {saved_result.id}")
        
        return saved_result

    except HTTPException:
        # Re-raise HTTPExceptions directly, as they are intentional errors
        raise
    except ValidationError as e:
        logger.error(f"Pydantic Validation Error during analysis for URL: {url}, User: {user_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data validation error: {e.errors()}"
        )
    except Exception as e:
        # Catch any other unexpected errors during the analysis process
        logger.critical(f"CRITICAL Analysis Error: An unhandled exception occurred during analysis of {url} for user {user_id}. Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error during analysis: {e}. Please check server logs for details."
        )

# --- REMOVED REDUNDANT REPORT ROUTES ---
# The /reports/user/{user_id} and /reports/{report_id} endpoints
# have been moved to backend/app/routers/report_routes.py
# to avoid redundancy and centralize report fetching logic.