from pydantic import BaseModel


class SpeechQualityResponse(BaseModel):
    id: int
    speech_id: int
    meeting_name: str | None = None
    speech_date: str | None = None
    speech_chars: int = 0
    policy_relevance: float = 0.0
    constructiveness: float = 0.0
    expertise: float = 0.0
    national_interest: float = 0.0
    overall_quality: float = 0.0
    analysis_summary: str | None = None

    model_config = {"from_attributes": True}
