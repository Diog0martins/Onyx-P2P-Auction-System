from pydantic import BaseModel, Field
from typing import Optional

# Entra no /register
class RegisterReq(BaseModel):
    user_pub: str = Field(..., description="RSA public key (PEM/base64)")
    display_name: Optional[str] = Field(None, description="Optional metadata")

# Sai do /register
class RegisterResp(BaseModel):
    uid: str
    cert: dict
    cert_sig: str
    ca_pub: str
    token_quota: int