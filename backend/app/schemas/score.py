from pydantic import BaseModel

from app.schemas.member import MemberResponse


class ScoreResponse(BaseModel):
    id: int
    member_id: int
    session_id: int
    legislative_activity_raw: float = 0.0
    voting_behavior_raw: float = 0.0
    policy_influence_raw: float = 0.0
    transparency_raw: float = 0.0
    legislative_activity: float = 0.0
    voting_behavior: float = 0.0
    policy_influence: float = 0.0
    transparency: float = 0.0
    total: float = 0.0
    grade: str = "F"
    breakdown: dict | None = None

    model_config = {"from_attributes": True}


class RankingEntry(BaseModel):
    rank: int
    member: MemberResponse
    score: ScoreResponse


class RankingResponse(BaseModel):
    items: list[RankingEntry]
    total: int
    chamber: str | None = None
    party: str | None = None
    session_number: int | None = None


class ScoreDistribution(BaseModel):
    grade: str
    count: int
    percentage: float


class StatsResponse(BaseModel):
    total_members: int
    average_score: float
    median_score: float
    max_score: float
    min_score: float
    distribution: list[ScoreDistribution]
    chamber: str | None = None
    session_number: int | None = None
