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
