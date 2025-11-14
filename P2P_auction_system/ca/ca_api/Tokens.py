from pydantic import BaseModel, Field
from typing import List

# Entra no /tokens
class TokensReq(BaseModel):
    uid: str
    count: int = Field(ge=1, le=100)

# Sai do /tokens
class TokensResp(BaseModel):
    uid: str
    issued: List[str]