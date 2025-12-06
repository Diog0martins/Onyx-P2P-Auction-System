from pydantic import BaseModel, Field
from typing import List

# Enter /tokens
class TokensReq(BaseModel):
    uid: str
    count: int = Field(ge=1, le=100)

# Leave /tokens
class TokensResp(BaseModel):
    uid: str
    issued: List[str]