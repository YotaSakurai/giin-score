from pydantic import BaseModel


class BillBase(BaseModel):
    bill_kind: str
    bill_number: str | None = None
    title: str
    status: str | None = None
    result: str | None = None
    proposer_type: str | None = None


class BillResponse(BillBase):
    id: int
    session_id: int
    url: str | None = None

    model_config = {"from_attributes": True}


class SponsorInfo(BaseModel):
    member_id: int
    member_name: str
    sponsor_type: str

    model_config = {"from_attributes": True}


class VoteResultSummary(BaseModel):
    id: int
    chamber: str
    ayes: int = 0
    nays: int = 0
    result: str | None = None

    model_config = {"from_attributes": True}


class BillDetail(BillResponse):
    sponsors: list[SponsorInfo] = []
    vote_results: list[VoteResultSummary] = []

    model_config = {"from_attributes": True}
