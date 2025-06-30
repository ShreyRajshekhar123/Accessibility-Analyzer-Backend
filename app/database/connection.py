# backend/app/database/connection.py

import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure

from app.config import settings # Assuming settings from app.config

logger = logging.getLogger("accessibility_analyzer_backend.database.connection")

client: Optional[AsyncIOMotorClient] = None
db_instance = None # To hold the database object
reports_collection_instance = None # To hold the specific collection for reports

async def connect_to_mongo():
    global client, db_instance, reports_collection_instance

    MONGO_URI = settings.MONGODB_URI
    MONGO_DB_NAME = settings.MONGODB_DB_NAME
    # It's good practice to get collection name from settings too, or hardcode it
    # For consistency with frontend and 'reports' in route, let's hardcode 'reports' for now
    # Or add a setting like REPORTS_COLLECTION_NAME: str = "reports" in config.py
    REPORTS_COLLECTION_NAME = "reports" # Changed from MONGO_COLLECTION_NAME, assuming 'reports'

    try:
        logger.info(f"Attempting to connect to MongoDB at: {MONGO_URI} for database: {MONGO_DB_NAME}")
        client = AsyncIOMotorClient(MONGO_URI)
        db_instance = client[MONGO_DB_NAME]
        reports_collection_instance = db_instance[REPORTS_COLLECTION_NAME] # Corrected collection name

        await client.admin.command('ping')
        logger.info("MongoDB connection established successfully.")

        try:
            # Create indexes specifically for the 'reports' collection
            await reports_collection_instance.create_index("user_id")
            await reports_collection_instance.create_index([("url", 1), ("user_id", 1)], unique=True)
            logger.info(f"MongoDB indexes for '{REPORTS_COLLECTION_NAME}' collection ensured.")
        except OperationFailure as e:
            logger.warning(f"MongoDB index creation warning for '{REPORTS_COLLECTION_NAME}': {e}. If indexes already exist, this is fine.")

    except ConnectionFailure as e:
        logger.critical(f"CRITICAL: Could not connect to MongoDB at {MONGO_URI}. "
                        f"Please ensure MongoDB is running and accessible. Error: {e}")
        client = None
        db_instance = None
        reports_collection_instance = None
        raise
    except Exception as e:
        logger.critical(f"An unexpected and critical error occurred during MongoDB connection setup: {e}")
        client = None
        db_instance = None
        reports_collection_instance = None
        raise

async def close_mongo_connection():
    global client, db_instance, reports_collection_instance
    if client:
        client.close()
        logger.info("MongoDB connection closed.")
        client = None
        db_instance = None
        reports_collection_instance = None # Clear this too

def get_database():
    """Returns the connected MongoDB database instance."""
    if db_instance is None:
        error_msg = "MongoDB database instance is not initialized. Ensure connect_to_mongo() was called successfully."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return db_instance

def get_reports_collection():
    """Returns the MongoDB collection instance for accessibility reports."""
    if reports_collection_instance is None:
        error_msg = "MongoDB reports collection is not initialized. Ensure connect_to_mongo() was called successfully."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return reports_collection_instance