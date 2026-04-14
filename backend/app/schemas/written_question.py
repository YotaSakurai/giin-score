from pydantic import BaseModel


class WrittenQuestionResponse(BaseModel):
    id: int
    session_id: int
    question_number: int
    title: str
    submitted_date: str | None = None
    answer_date: str | None = None
    question_url: str | None = None
    answer_url: str | None = None
    has_answer: bool

    model_config = {"from_attributes": True}
