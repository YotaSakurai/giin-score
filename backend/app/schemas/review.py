from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    reviewer_id: str = Field(..., max_length=36)
    display_name: str | None = Field(None, max_length=50)
    legislative_activity: float = Field(50.0, ge=0, le=100)
    voting_behavior: float = Field(50.0, ge=0, le=100)
    policy_influence: float = Field(50.0, ge=0, le=100)
    transparency: float = Field(50.0, ge=0, le=100)
    question_quality: float = Field(50.0, ge=0, le=100)
    comment: str | None = Field(None, max_length=1000)


class ReviewUpdate(BaseModel):
    reviewer_id: str = Field(..., max_length=36)
    display_name: str | None = Field(None, max_length=50)
    legislative_activity: float | None = Field(None, ge=0, le=100)
    voting_behavior: float | None = Field(None, ge=0, le=100)
    policy_influence: float | None = Field(None, ge=0, le=100)
    transparency: float | None = Field(None, ge=0, le=100)
    question_quality: float | None = Field(None, ge=0, le=100)
    comment: str | None = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    member_id: int
    reviewer_id: str
    display_name: str | None
    legislative_activity: float
    voting_behavior: float
    policy_influence: float
    transparency: float
    question_quality: float
    total: float
    comment: str | None
    like_count: int
    is_liked: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewSummary(BaseModel):
    member_id: int
    review_count: int
    average_legislative_activity: float
    average_voting_behavior: float
    average_policy_influence: float
    average_transparency: float
    average_question_quality: float
    average_total: float


class LikeToggleRequest(BaseModel):
    liker_id: str = Field(..., max_length=36)
