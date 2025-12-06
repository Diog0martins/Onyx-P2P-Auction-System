from pydantic import BaseModel, Field
from typing import Optional

# Enter /register
class RegisterReq(BaseModel):
    csr_pem_b64: str = Field(..., description="Base64-encoded PEM CSR")


# Leave /register
class RegisterResp(BaseModel):
    uid: str
    cert_pem_b64: str
    ca_pub_pem_b64: str
    group_key_b64: str
    token_quota: int
