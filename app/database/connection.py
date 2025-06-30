# backend/app/database/connection.py

import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure

# --- Import settings from your config ---
# This import assumes that app/config.py exists and defines a 'settings' object
# which is an instance of a pydantic_settings BaseSettings class.
from app.config import settings

logger = logging.getLogger("accessibility_analyzer_backend.database.connection")

# Global variables to hold the MongoDB client and collection instance
client: Optional[AsyncIOMotorClient] = None
analysis_collection = None # This will be set on successful connection

async def connect_to_mongo():
    """
    Establishes a connection to MongoDB and sets up the global client and collection.
    """
    global client, analysis_collection

    # --- USE THE SETTINGS OBJECT FOR MONGODB_URI AND MONGODB_DB_NAME ---
    # These values are now populated from environment variables (or .env file)
    # via the pydantic-settings in app.config.py
    MONGO_URI = settings.MONGODB_URI
    MONGO_DB_NAME = settings.MONGODB_DB_NAME

    # For MONGO_COLLECTION_NAME, if it's not in your settings, you can keep os.getenv
    # or hardcode it if it's always "analysis_results".
    MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "analysis_results")


    try:
        logger.info(f"Attempting to connect to MongoDB at: {MONGO_URI} for database: {MONGO_DB_NAME}")
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        analysis_collection = db[MONGO_COLLECTION_NAME]

        # Ping the server to ensure the connection is active
        await client.admin.command('ping')
        logger.info("MongoDB connection established successfully.")

        # Optional: Ensure indexes here if not handled elsewhere (e.g., in repository)
        # It's generally good practice to ensure indexes on startup
        try:
            # Create indexes for efficient querying by user_id and for unique URL/user_id combinations
            await analysis_collection.create_index("user_id")
            await analysis_collection.create_index([("url", 1), ("user_id", 1)], unique=True)
            logger.info("MongoDB indexes for 'analysis_results' collection ensured.")
        except OperationFailure as e:
            logger.warning(f"MongoDB index creation warning: {e}. If indexes already exist, this is fine.")


    except ConnectionFailure as e:
        logger.critical(f"CRITICAL: Could not connect to MongoDB at {MONGO_URI}. "
                         f"Please ensure MongoDB is running and accessible. Error: {e}")
        client = None
        analysis_collection = None
        # Re-raise the exception to propagate the critical error and stop the app startup if DB connection fails
        raise

    except Exception as e:
        logger.critical(f"An unexpected and critical error occurred during MongoDB connection setup: {e}")
        client = None
        analysis_collection = None
        # Re-raise the exception to propagate the critical error and stop the app startup
        raise

async def close_mongo_connection():
    """
    Closes the MongoDB connection.
    """
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")
        client = None # Clear the client reference

def get_analysis_collection():
    """
    Returns the MongoDB collection instance for analysis results.
    Raises an exception if the connection has not been established.
    """
    if analysis_collection is None:
        error_msg = "MongoDB analysis collection is not initialized. Ensure connect_to_mongo() was called successfully."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return analysis_collection