from datetime import date

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: int
    session_number: int
    kind: str
    start_date: date | None = None
    end_date: date | None = None

    model_config = {"from_attributes": True}
