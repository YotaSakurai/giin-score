from pydantic import BaseModel


class VoteResultResponse(BaseModel):
    id: int
    bill_id: int
    bill_title: str | None = None
    chamber: str
    ayes: int = 0
    nays: int = 0
    result: str | None = None

    model_config = {"from_attributes": True}


class VoteRecordResponse(BaseModel):
    id: int
    vote_result_id: int
    member_id: int
    member_name: str | None = None
    vote: str
    bill_title: str | None = None

    model_config = {"from_attributes": True}


class VotePatternResponse(BaseModel):
    """投票パターン分析結果"""

    member_id: int
    total_votes: int
    party_majority_votes: int
    dissent_votes: int
    dissent_rate: float
    absent_count: int
    participation_rate: float
    dissent_details: list["DissentDetail"]


class DissentDetail(BaseModel):
    """造反投票の詳細"""

    bill_title: str | None = None
    member_vote: str
    party_majority_vote: str
