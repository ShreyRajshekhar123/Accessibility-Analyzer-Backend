from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional
from bson import ObjectId # Required for MongoDB ObjectId
from pydantic_core import core_schema # Import core_schema for Pydantic v2 custom types

# Custom type for ObjectId to work seamlessly with Pydantic v2
class PyObjectId(ObjectId):
    """
    Custom ObjectId class for Pydantic v2.
    It allows Pydantic to validate and serialize MongoDB ObjectIds.
    """
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler) -> core_schema.CoreSchema:
        """
        Returns the Pydantic CoreSchema for PyObjectId.
        This defines how Pydantic validates and serializes the type internally.
        """
        return core_schema.no_info_after_validator_function(
            cls.validate, # Use our custom validation method
            core_schema.str_schema(), # Treat it as a string for basic schema generation
            serialization=core_schema.to_string_ser_schema(), # Serialize to string when converting to JSON
        )

    @classmethod
    def validate(cls, value: Any) -> ObjectId:
        """
        Custom validation logic for converting a value to an ObjectId.
        Handles both existing ObjectId instances and string representations.
        """
        if isinstance(value, ObjectId):
            return value
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler) -> core_schema.JsonSchema:
        """
        Returns the JSON schema for PyObjectId.
        This is used for OpenAPI/Swagger documentation, ensuring 'id' fields
        are correctly represented as strings.
        """
        json_schema = handler(core_schema)
        json_schema.update(
            type="string",
            format="mongo-id", # Optional: custom format hint for documentation
            example="60c72b2f9b1e8e2b0c1c2b3d" # Example for documentation
        )
        return json_schema

class AnalysisRequest(BaseModel):
    url: HttpUrl = Field(..., example="https://www.google.com")

class AiSuggestion(BaseModel):
    short_fix: str
    detailed_fix: str

class IssueNode(BaseModel):
    html: str
    target: List[str]
    # Add more fields if axe-core provides them, e.g., 'impact', 'any', 'all', 'none'

class Issue(BaseModel):
    id: str
    description: str
    help: str
    severity: str # e.g., "critical", "moderate", "minor", "suggestion"
    nodes: List[IssueNode] = []
    ai_suggestions: Optional[AiSuggestion] = None # Will be populated in Phase 4

class AnalysisSummary(BaseModel):
    total_issues: int
    critical: int
    moderate: int
    minor: int
    score: Optional[int] = None # Added score field

class AnalysisResult(BaseModel):
    # This field maps the MongoDB '_id' to a Pydantic 'id' field, handling type conversion.
    # default_factory=PyObjectId ensures a new ObjectId is generated if 'id' isn't provided during creation.
    id: Optional[PyObjectId] = Field(alias="_id", default_factory=PyObjectId)
    url: HttpUrl
    timestamp: str 
    summary: AnalysisSummary
    issues: List[Issue]
    page_title: Optional[str] = None # Added to store and display page title

    class Config:
        # Allows Pydantic to populate model fields using either the field name ('id') or its alias ('_id').
        populate_by_name = True
        # Custom JSON encoder to convert ObjectId objects to strings when serializing the model to JSON.
        # This is primarily for the *output* JSON. The PyObjectId class handles validation *input*.
        json_encoders = {ObjectId: str}
        # Added for Pydantic v2 compatibility when handling custom types as fields
        arbitrary_types_allowed = True
