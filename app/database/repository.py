# backend/app/database/repository.py

import logging
from typing import List, Optional
import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from pydantic import HttpUrl
import traceback # Import traceback for detailed error logging

# --- CRITICAL FIX: Correct Import Paths based on your schemas.py location ---
from ..schemas import AnalysisResult, PyObjectId # Changed from app.models.report

# --- IMPORTANT FIX: Use get_reports_collection for consistency ---
from .connection import get_reports_collection 

logger = logging.getLogger("accessibility_analyzer_backend.database.repository")

# --- SUGGESTED RENAME: Consider renaming AnalysisRepository to ReportRepository ---
# This class primarily handles 'AnalysisResult' objects which are 'reports'.
class AnalysisRepository: 
    """
    Handles CRUD operations for accessibility analysis results (reports) in MongoDB.
    """
    def __init__(self):
        # Initialize with the correctly named reports collection
        self.collection = get_reports_collection() 
        if self.collection is None:
            # This critical log should ideally not be hit if main.py and connection.py
            # handle startup connection errors properly by exiting.
            logger.critical("AnalysisRepository initialized without a valid MongoDB collection. Database operations will likely fail.")
            # Raising an error here could also be an option to prevent method calls
            # on a non-existent collection, but app startup should ideally prevent this.

    async def get_analysis_by_url_and_user(self, url: HttpUrl, user_id: str) -> Optional[AnalysisResult]:
        """
        Fetches an accessibility analysis report from the cache by URL and user ID.
        """
        try:
            # Ensure url is stored as string in MongoDB
            cached_result_doc = await self.collection.find_one({"url": str(url), "user_id": user_id})

            if cached_result_doc:
                logger.info(f"Cache Hit: Retrieved cached analysis for URL: {url} | User: {user_id}")
                # Use model_validate for Pydantic V2 to correctly parse MongoDB document
                # This will handle _id to PyObjectId conversion automatically if schema is correct
                return AnalysisResult.model_validate(cached_result_doc)
            
            logger.info(f"Cache Miss: No cached analysis found for URL: {url} | User: {user_id}.")
            return None
        except PyMongoError as e:
            logger.error(f"MongoDB Error in get_analysis_by_url_and_user for URL: {url}, User: {user_id}. Error: {e}", exc_info=True)
            return None 
        except Exception as e:
            logger.error(f"Error validating cached document for URL: {url}, User: {user_id}. Error: {e}", exc_info=True)
            return None


    async def save_analysis_result(self, analysis_result: AnalysisResult) -> AnalysisResult:
        """
        Saves or updates an accessibility analysis report in MongoDB.
        If a report for the given URL and user_id already exists, it updates it.
        Otherwise, it inserts a new one.
        Returns the AnalysisResult with its database ID populated.
        """
        try:
            # Pydantic's model_dump(by_alias=True) will convert 'id' to '_id' for MongoDB
            # and PyObjectId to ObjectId for storage, and exclude_none will remove None values
            doc_to_save = analysis_result.model_dump(by_alias=True, exclude_none=True)
            doc_to_save['url'] = str(analysis_result.url) # Ensure HttpUrl is stored as string

            # Ensure timestamp is set or updated
            doc_to_save['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

            update_result = await self.collection.update_one(
                {"url": doc_to_save['url'], "user_id": doc_to_save['user_id']}, # Query by url AND user_id
                {"$set": doc_to_save},
                upsert=True
            )

            if update_result.upserted_id:
                # If a new document was inserted, update the Pydantic model's ID
                analysis_result.id = PyObjectId(update_result.upserted_id)
                logger.info(f"MongoDB Save: New analysis result for {analysis_result.url} by user {analysis_result.user_id} inserted with ID: {update_result.upserted_id}")
            else:
                # If an existing document was updated, we need to ensure its _id is correctly set
                # (since update_one doesn't return the _id of an updated doc by default,
                # but the `analysis_result` object should already have it from the input or previous save)
                if analysis_result.id is None: # Fallback in case ID was not set on input model
                    existing_doc = await self.collection.find_one({"url": doc_to_save['url'], "user_id": doc_to_save['user_id']}, {"_id": 1})
                    if existing_doc:
                        analysis_result.id = PyObjectId(existing_doc['_id'])
                logger.info(f"MongoDB Save: Existing analysis result for {analysis_result.url} by user {analysis_result.user_id} updated.")
            
            return analysis_result
        except PyMongoError as e:
            logger.error(f"MongoDB Save Error: Failed to save/update analysis result for URL: {analysis_result.url}, User: {analysis_result.user_id}. Error: {e}", exc_info=True)
            raise # Re-raise for error handling in calling API route
        except Exception as e:
            logger.error(f"Unexpected error saving analysis result for URL: {analysis_result.url}, User: {analysis_result.user_id}. Error: {e}", exc_info=True)
            raise


    async def get_all_user_analysis_results(self, user_id: str) -> List[AnalysisResult]:
        """
        Fetches all accessibility analysis reports for a given user ID.
        """
        reports: List[AnalysisResult] = []
        try:
            cursor = self.collection.find({"user_id": user_id}).sort("timestamp", -1)
            docs_list = await cursor.to_list(None)

            for doc in docs_list:
                try:
                    # Use model_validate for Pydantic V2 to correctly parse MongoDB document
                    # This handles _id to PyObjectId conversion automatically
                    reports.append(AnalysisResult.model_validate(doc))
                except Exception as e:
                    logger.error(f"Report Parsing Error: Could not parse document from DB for user {user_id}. Document ID: {doc.get('_id', 'N/A')}. Error: {e}", exc_info=True)
                    logger.error(f"Malformed Document Content (skipped): {doc}")
                    continue # Skip this malformed document and continue with others

            logger.info(f"Report Fetch Success: Found {len(reports)} reports for user: {user_id}")
            return reports
        except PyMongoError as e:
            logger.error(f"MongoDB Fetch Error: Failed to retrieve all reports for user: {user_id}. Error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching all reports for user: {user_id}. Error: {e}", exc_info=True)
            raise


    async def get_single_analysis_result_by_id(self, report_id: str, user_id: str) -> Optional[AnalysisResult]:
        """
        Fetches a single detailed accessibility report by its unique MongoDB _id.
        Ensures the report belongs to the specified user.
        """
        try:
            # Convert report_id string to MongoDB ObjectId
            obj_id = ObjectId(report_id)
        except InvalidId as e: # Catch specific InvalidId error
            logger.warning(f"Invalid report ID format provided: '{report_id}'. Error: {e}")
            # Re-raise as ValueError for the API layer to catch and convert to HTTPException
            raise ValueError(f"Invalid report ID format: {report_id}") from e 
        except Exception as e: # Catch any other unexpected errors during conversion
            logger.error(f"Unexpected error during ObjectId conversion for ID: '{report_id}'. Error: {e}", exc_info=True)
            raise ValueError(f"Invalid report ID format: {report_id}") from e 


        try:
            # Find the report by _id AND user_id for security
            report_doc = await self.collection.find_one({
                "_id": obj_id,
                "user_id": user_id # Crucial security check: only allow users to see their own reports
            })

            if report_doc:
                logger.info(f"Single Report Fetch Success: Report {report_id} found for user {user_id}.")
                # Use model_validate for Pydantic V2 to correctly parse MongoDB document
                return AnalysisResult.model_validate(report_doc)
            else:
                logger.warning(f"Single Report Not Found: Report ID {report_id} not found or does not belong to user {user_id}.")
                return None # Return None if not found/authorized
        except PyMongoError as e:
            logger.error(f"MongoDB Fetch Error: Failed to retrieve report {report_id} for user {user_id}. Error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching report {report_id} for user {user_id}. Error: {e}", exc_info=True)
            raise