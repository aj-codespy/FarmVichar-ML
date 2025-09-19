# schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

# --- Core API Schemas ---

class ChatResponse(BaseModel):
    """ Defines the response from the /chat endpoint. """
    response_text: str
    transcribed_text: Optional[str] = None

class DashboardData(BaseModel):
    """ Defines the structure of the data returned for the dashboard. """
    user_profile: Dict[str, Any]
    weather: dict
    predictions: "DashboardPredictions" # Forward reference

class Alert(BaseModel):
    """ Defines the structure for a single proactive alert. """
    id: str
    severity: str
    title: str
    message: str
    suggestion: str

class AlertsResponse(BaseModel):
    """ Defines the response for the /alerts endpoint. """
    alerts: List[Alert]

# --- Logging Schemas ---

class LogEntry(BaseModel):
    """
    Defines a FLEXIBLE format for a farmer's log entry. The AI will parse this.
    """
    notes: str 
    log_type: Optional[str] = None
    date: Optional[str] = None
    crop_name: Optional[str] = None
    summary: Optional[str] = None  # <-- Add this line
    details: Optional[Dict[str, Any]] = None

class LogAnalysisResponse(BaseModel):
    """
    Defines the structured output from the AI after analyzing a log.
    """
    summary: str
    risk_level: str
    risk_description: str
    structured_log_data: LogEntry # The AI's structured interpretation of the log
    suggested_action: str

class VoiceLogResponse(BaseModel):
    """
    Defines the response from the voice-to-log endpoint.
    """
    transcribed_text: str
    structured_log: LogEntry

# --- Onboarding Schemas ---

class OnboardingVoiceRequest(BaseModel):
    """ Defines the data sent with the audio for a single form field. """
    field_name: str
    context_question: str

class OnboardingVoiceResponse(BaseModel):
    """ Defines the response for a single, extracted value for a form field. """
    transcribed_text: str
    extracted_value: Any

# --- Nested Schemas for Dashboard ---

class PriceRange(BaseModel):
    crop_name: str
    min_price: int
    max_price: int

class StructuredLog(BaseModel):
    log_type: str
    date: str
    crop_name: Optional[str]
    summary: str
    details: Union[Dict[str, str], str] = Field(default_factory=dict)

class DashboardPredictions(BaseModel):
    """
    Defines the structured output for all predictions on the dashboard.
    """
    recommended_crop: str
    yield_prediction_kg_acre: float
    pest_risk_percent: int
    quality_grading_score: int
    price_range_per_quintal: PriceRange
    applicable_schemes: List[str]
    applied_schemes: List[str]

# This line is important for Pydantic to resolve the forward reference
DashboardData.model_rebuild()

from typing import Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class GeoLocation(BaseModel):
    latitude: Optional[float] = Field(None, description="Latitude in decimal degrees")
    longitude: Optional[float] = Field(None, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

class FarmLog(BaseModel):
    farmId: str
    activityType: str
    description: str
    geoLocation: Optional[GeoLocation] = None
    id: Optional[str] = None
    timestamp: datetime