from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional

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
    score: Optional[int] = None # <-- THIS IS THE CRUCIAL ADDITION FOR THE SCORE
    # Add more categories as needed

class AnalysisResult(BaseModel):
    url: HttpUrl
    timestamp: str # Using string for simplicity, can use datetime object
    summary: AnalysisSummary
    issues: List[Issue]
    # Add other relevant analysis data here
