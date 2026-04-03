from pydantic import BaseModel


class MemberBase(BaseModel):
    name: str
    name_reading: str | None = None
    chamber: str
    party: str | None = None
    faction: str | None = None
    district: str | None = None
    role_category: str | None = None


class MemberResponse(MemberBase):
    id: int

    model_config = {"from_attributes": True}


class ScoreSummary(BaseModel):
    total: float = 0.0
    grade: str = "F"
    legislative_activity: float = 0.0
    voting_behavior: float = 0.0
    policy_influence: float = 0.0
    transparency: float = 0.0
    question_quality: float = 0.0

    model_config = {"from_attributes": True}


class MemberWithScore(MemberResponse):
    latest_score: ScoreSummary | None = None


class MemberDetail(MemberResponse):
    scores: list["ScoreDetail"] = []

    model_config = {"from_attributes": True}


class MemberScorePoint(BaseModel):
    id: int
    name: str
    party: str | None = None
    chamber: str
    grade: str = "F"
    total: float = 0.0
    legislative_activity: float = 0.0
    voting_behavior: float = 0.0
    policy_influence: float = 0.0
    transparency: float = 0.0
    question_quality: float = 0.0


class ScoreDetail(BaseModel):
    id: int
    session_id: int
    session_number: int | None = None
    legislative_activity_raw: float = 0.0
    voting_behavior_raw: float = 0.0
    policy_influence_raw: float = 0.0
    transparency_raw: float = 0.0
    question_quality_raw: float = 0.0
    legislative_activity: float = 0.0
    voting_behavior: float = 0.0
    policy_influence: float = 0.0
    transparency: float = 0.0
    question_quality: float = 0.0
    total: float = 0.0
    grade: str = "F"
    breakdown: dict | None = None

    model_config = {"from_attributes": True}
