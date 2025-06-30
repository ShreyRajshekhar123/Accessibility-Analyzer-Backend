# backend/app/routers/report_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
from bson import ObjectId # Still needed here for the delete route's direct DB call temporarily

# --- CRITICAL FIX: Use the correct schema import path ---
# Assuming AnalysisResult is your primary report schema (previously ReportDB)
from ..schemas import AnalysisResult 

# --- IMPORTANT: Import AnalysisRepository ---
from ..database.repository import AnalysisRepository
from app.auth.auth_dependency import get_current_user_firebase # For protected routes
from app.database.connection import get_database # Keep for temporary delete_report direct DB call

logger = logging.getLogger("accessibility_analyzer_backend.report_routes")

router = APIRouter()

# --- REMOVED: convert_object_id helper is no longer needed with PyObjectId in schema ---

# Dependency to get the repository instance
def get_analysis_repository() -> AnalysisRepository:
    """
    Dependency function to provide an instance of AnalysisRepository.
    """
    return AnalysisRepository()

# Get all reports for a specific user
@router.get("/reports/user/{user_uid}", response_model=List[AnalysisResult], summary="Get all reports for a specific user")
async def get_user_reports(
    user_uid: str,
    current_user: dict = Depends(get_current_user_firebase),
    repository: AnalysisRepository = Depends(get_analysis_repository) # Use repository dependency
):
    """
    Retrieves all accessibility reports associated with a given user UID.
    The authenticated user's UID must match the requested user_uid.
    """
    # Security check: Ensure the authenticated user is accessing their own reports
    if current_user["uid"] != user_uid:
        logger.warning(f"Unauthorized attempt to access reports for user_uid: {user_uid} by current_user: {current_user['uid']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view these reports."
        )

    try:
        # Use the repository method to fetch reports
        reports = await repository.get_all_user_analysis_results(user_uid)
        logger.info(f"Fetched {len(reports)} reports for user: {user_uid}")
        # Pydantic (AnalysisResult model) will automatically handle the ObjectId to string conversion for the response
        return reports 
    except Exception as e:
        logger.error(f"Error fetching reports for user {user_uid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve reports."
        )

# Get a single report by its ID
@router.get("/reports/{report_id}", response_model=AnalysisResult, summary="Get a single report by ID")
async def get_single_report(
    report_id: str,
    current_user: dict = Depends(get_current_user_firebase),
    repository: AnalysisRepository = Depends(get_analysis_repository) # Use repository dependency
):
    """
    Retrieves a single accessibility report by its unique ID.
    The authenticated user must be the owner of the report.
    """
    try:
        # Use the repository method to fetch the report.
        # The repository method already includes the user_id in its query for security.
        report = await repository.get_single_analysis_result_by_id(report_id, current_user["uid"])
        
        if not report:
            # If the report is None, it means it wasn't found OR the user was not authorized
            logger.warning(f"Report not found with ID: {report_id} or unauthorized access attempt by user: {current_user['uid']}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or you are not authorized to view it.")
        
        logger.info(f"Fetched report {report_id} for user: {current_user['uid']}")
        # Pydantic (AnalysisResult model) will automatically handle the ObjectId to string conversion for the response
        return report 
    except ValueError as ve: # Catch specific error from repository if ID format is invalid
        logger.warning(f"Invalid report ID format provided: {report_id}. Error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve) # Pass the specific error message from the ValueError
        )
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve report."
        )

# Example: Delete a report (will use direct DB access temporarily until repo method is added)
@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a report by ID")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user_firebase),
    # repository: AnalysisRepository = Depends(get_analysis_repository) # Uncomment when repository method is ready
):
    """
    Deletes an accessibility report by its unique ID.
    The authenticated user must be the owner of the report.
    """
    try:
        # NOTE: A `delete_report` method should ideally be added to `AnalysisRepository`
        # for full consistency and separation of concerns.
        # For now, we'll use direct DB interaction, similar to your original code.
        
        db = get_database()
        reports_collection = db["reports"]

        # 1. Find the report to verify ownership
        report_to_delete = await reports_collection.find_one({"_id": ObjectId(report_id)})
        
        if not report_to_delete:
            logger.warning(f"Report not found with ID: {report_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
        if report_to_delete.get("user_id") != current_user["uid"]:
            logger.warning(f"Unauthorized attempt to delete report {report_id} by user: {current_user['uid']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this report."
            )
        
        # 2. Delete the report
        delete_result = await reports_collection.delete_one({"_id": ObjectId(report_id)})
        
        if delete_result.deleted_count == 0:
            # This might happen in a very rare race condition or if the ID wasn't found despite the find_one
            logger.warning(f"Report {report_id} not found for deletion after ownership check (race condition?).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found for deletion.")
        
        logger.info(f"Report {report_id} deleted by user: {current_user['uid']}")
        return {} # FastAPI automatically handles 204 No Content for empty dict/None

    except ValueError as ve: # Catch specific error if report_id is not a valid ObjectId string
        logger.warning(f"Invalid report ID format provided for deletion: {report_id}. Error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve) # Pass the specific error message
        )
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete report."
        )