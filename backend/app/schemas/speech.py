from pydantic import BaseModel


class SpeechResponse(BaseModel):
    id: int
    meeting_name: str | None = None
    speech_date: str | None = None
    speech_chars: int = 0
    speech_url: str | None = None

    model_config = {"from_attributes": True}
