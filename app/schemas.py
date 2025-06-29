# backend/app/schemas.py

from pydantic import BaseModel, HttpUrl, Field, GetCoreSchemaHandler
from typing import List, Dict, Any, Optional, ClassVar
from bson import ObjectId
from pydantic_core import core_schema
from datetime import datetime, timezone

# --- REVISED PyObjectId Definition (Crucial for validation) ---
class PyObjectId(ObjectId):
    """
    Custom type for MongoDB's ObjectId to work seamlessly with Pydantic v2.
    Handles both validation from MongoDB (ObjectId) and string, and serialization to string.
    """

    @classmethod
    def __get_validators__(cls):
        # This method is for Pydantic V1 compatibility or when used with Annotated.
        # For V2, __get_pydantic_core_schema__ is more direct.
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        """
        Custom validation logic for converting a value to an ObjectId.
        Handles both existing ObjectId instances and string representations.
        """
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            if ObjectId.is_valid(v): # Check if the string is a valid ObjectId
                return ObjectId(v)
            raise ValueError(f"Invalid ObjectId string: '{v}'")
        raise ValueError("Invalid ObjectId type or format")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """
        Defines the Pydantic v2 core schema for PyObjectId, including validation and serialization.
        """
        # This creates a 'union' schema. It tries to parse the input as a string first,
        # and if that fails, it tries to directly accept a bson.ObjectId.
        # Then, after validation, it applies `cls.validate`.
        # For serialization, it explicitly converts to a string.
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId), # Allow direct ObjectId instance
                core_schema.str_schema() # Allow string representation
            ]),
            serialization=core_schema.to_string_ser_schema() # Always serialize to string
        )

    # Required for Pydantic to handle default_factory and comparison correctly
    def __eq__(self, other):
        if isinstance(other, ObjectId):
            return self.binary == other.binary
        return NotImplemented

    def __hash__(self):
        return self.binary.__hash__()

# --- Analysis Request Schema (for POST /analyze) ---
class AnalysisRequest(BaseModel):
    url: HttpUrl = Field(..., example="https://www.google.com")

# ... (rest of your schemas remain exactly the same as previously provided) ...

# --- AI Suggestion Schema ---
class AiSuggestion(BaseModel):
    """Represents an AI-generated suggestion for an accessibility issue."""
    short_fix: str = Field(..., example="Add alt text to the image.")
    detailed_fix: str = Field(..., example="Ensure all <img> tags have a descriptive `alt` attribute. If the image is decorative, use `alt=\"\"`.")

# --- Issue Node Schema ---
class IssueNode(BaseModel):
    """Represents an affected element identified by accessibility scan (e.g., from Axe-core)."""
    html: Optional[str] = Field(None, example="<img src='logo.png'>")
    target: List[str] = Field(..., example=["img[src='logo.png']"]) # CSS selector or array of selectors
    snippet: Optional[str] = Field(None, example="<img src='logo.png' alt=''>") # A snippet of the problematic HTML
    failureSummary: Optional[str] = Field(None, example="Element does not have an alt attribute.") # Summary of why the rule failed for this node
    xpath: Optional[str] = Field(None, example="/html/body/img[1]") # XPath of the element
    
    model_config = { # Use model_config (dictionary) for Pydantic V2
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


# --- Issue Schema ---
class Issue(BaseModel):
    """Represents a single accessibility issue found."""
    id: str = Field(..., example="image-alt") # Axe-core's rule ID
    description: str = Field(..., example="Images must have alternate text.")
    help: str = Field(..., example="Ensure that the alt attribute of an image is not empty and describes the image.")
    helpUrl: Optional[HttpUrl] = Field(None, example="https://dequeuniversity.com/rules/axe/4.4/image-alt?application=axeAPI") # Changed to HttpUrl
    severity: str = Field(..., example="critical") # Corresponds to Axe-core's 'impact'
    tags: List[str] = Field([], example=["wcag2a", "wcag111", "cat.text-alternatives"])
    nodes: List[IssueNode] = Field([], example=[{
        "html": "<button id='myButton' style='color:red;background:pink;'>Click Me</button>",
        "target": ["#myButton"],
        "failureSummary": "Element has insufficient color contrast of 1.5:1 (foreground color: #ff0000, background color: #ffc0cb, required contrast ratio of 4.5:1).",
        "xpath": "/html/body/button"
    }])
    ai_suggestions: Optional[AiSuggestion] = None # Will be populated by AI helper

    model_config = { # Use model_config (dictionary)
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

# --- Analysis Summary Schema (UPDATED FIELD NAMES) ---
class AnalysisSummary(BaseModel):
    """Summary of the accessibility analysis results."""
    total_issues: int = Field(..., example=10)
    # Renamed fields to criticalIssues, moderateIssues, minorIssues
    criticalIssues: int = Field(..., example=2)
    moderateIssues: int = Field(..., example=5)
    minorIssues: int = Field(..., example=3)
    score: Optional[int] = Field(None, example=80, ge=0, le=100, description="Overall accessibility score out of 100.")

    model_config = { # Added model_config for consistency
        "populate_by_name": True
    }


# --- Analysis Result Schema (Full Report Document - UPDATED EXAMPLE) ---
class AnalysisResult(BaseModel):
    """Full accessibility analysis report, mapping to a MongoDB document."""
    # Now using the class PyObjectId directly
    id: PyObjectId = Field(alias="_id", default_factory=PyObjectId, description="Unique identifier for the analysis report (MongoDB ObjectId)")
    user_id: str = Field(..., example="firebase_user_id_123", description="The ID of the user who initiated the analysis")
    url: HttpUrl = Field(..., example="https://www.example.com", description="The URL that was analyzed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of when the analysis was performed (ISO 8601 format)")
    summary: AnalysisSummary = Field(..., description="Summary of the accessibility issues found")
    issues: List[Issue] = Field([], description="Detailed list of accessibility issues")
    page_title: Optional[str] = Field(None, example="Example Website Title", description="The title of the analyzed web page")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": { # This is now correctly nested within model_config
            "example": {
                "id": "60c72b2f9b1e8e2b0c1c2b3d",
                "user_id": "firebase_user_id_123",
                "url": "https://www.example.com",
                "timestamp": "2025-06-29T13:30:00.000Z", # ISO 8601 format example
                "summary": {
                    "total_issues": 10,
                    "criticalIssues": 2, # <-- UPDATED NAME HERE
                    "moderateIssues": 5, # <-- UPDATED NAME HERE
                    "minorIssues": 3,    # <-- UPDATED NAME HERE
                    "score": 80
                },
                "issues": [ # Simplified for example
                    {
                        "id": "color-contrast",
                        "description": "Elements must have sufficient color contrast.",
                        "help": "Ensure text and background colors have a sufficient contrast ratio.",
                        "helpUrl": "https://dequeuniversity.com/rules/axe/4.4/color-contrast",
                        "severity": "critical",
                        "tags": ["cat.color", "wcag2aa", "wcag143"],
                        "nodes": [
                            {
                                "html": "<button id='myButton' style='color:red;background:pink;'>Click Me</button>",
                                "target": ["#myButton"],
                                "snippet": "<button id='myButton' style='color:red;background:pink;'>Click Me</button>",
                                "failureSummary": "Element has insufficient color contrast of 1.5:1 (foreground color: #ff0000, background color: #ffc0cb, required contrast ratio of 4.5:1).",
                                "xpath": "/html/body/button"
                            }
                        ],
                        "ai_suggestions": {
                            "short_fix": "Improve color contrast.",
                            "detailed_fix": "Increase the contrast ratio of the button's text and background to at least 4.5:1 to meet WCAG AA standards."
                        }
                    }
                ],
                "page_title": "My Awesome Accessible Site"
            }
        }
    }