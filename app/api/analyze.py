# backend/app/api/analyze.py

from fastapi import APIRouter, HTTPException, Body, Depends, status
from pydantic import HttpUrl, ValidationError
from typing import List
import logging
import traceback
from bson.errors import InvalidId

# --- Import your schemas (data models) ---
from ..schemas import AnalysisRequest, AnalysisResult, Issue, AnalysisSummary, AiSuggestion, PyObjectId, IssueNode

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
# This is the line that was causing the TypeError if 'auth_dependency' was not callable
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
        raise
    except ValidationError as e:
        logger.error(f"Pydantic Validation Error during analysis for URL: {url}, User: {user_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data validation error: {e.errors()}"
        )
    except Exception as e:
        logger.critical(f"CRITICAL Analysis Error: An unhandled exception occurred during analysis of {url} for user {user_id}. Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error during analysis: {e}. Please check server logs for details."
        )


@router.get(
    "/reports/user/{user_id}",
    response_model=List[AnalysisResult],
    response_model_by_alias=True
)
async def get_user_reports(
    user_id: str,
    current_user: dict = current_user_dependency,
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository)
):
    """
    Fetches all accessibility analysis reports for a given user ID.
    """
    if user_id != current_user["uid"]:
        logger.warning(f"Unauthorized access attempt: User {current_user['uid']} tried to access reports for {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access these reports."
        )

    logger.info(f"API Request: GET /reports/user/{user_id} | Fetching all reports for user: {user_id}")

    try:
        reports = await analysis_repo.get_all_user_analysis_results(user_id)
        logger.info(f"Report Fetch Success: Found {len(reports)} reports for user: {user_id}")
        return reports
    except Exception as e:
        logger.error(f"Report Fetch Error: Failed to retrieve reports for user: {user_id}. Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user reports: {e}. Please try again later."
        )


@router.get(
    "/reports/{report_id}",
    response_model=AnalysisResult,
    response_model_by_alias=True
)
async def get_single_report(
    report_id: str,
    current_user: dict = current_user_dependency,
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository)
):
    """
    Fetches a single detailed accessibility report by its unique MongoDB _id.
    Ensures the report belongs to the authenticated user.
    """
    logger.info(f"API Request: GET /reports/{report_id} | Fetching single report for user: {current_user['uid']}")

    try:
        report = await analysis_repo.get_single_analysis_result_by_id(report_id, current_user["uid"])

        if report:
            logger.info(f"Single Report Fetch Success: Report {report_id} found for user {current_user['uid']}.")
            return report
        else:
            logger.warning(f"Single Report Not Found: Report ID {report_id} not found or does not belong to user {current_user['uid']}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found or you do not have permission to view it."
            )
    except InvalidId:
        logger.warning(f"Invalid report ID format provided: '{report_id}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report ID format. Must be a 24-character hexadecimal string."
        )
    except Exception as e:
        logger.error(f"Single Report Fetch Error: Failed to retrieve report {report_id} for user {current_user['uid']}. Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch report: {e}. Please try again later."
        )