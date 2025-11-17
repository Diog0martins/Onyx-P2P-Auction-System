from pydantic import BaseModel

class BlindSignReq(BaseModel):
    uid: str
    blinded_token_b64: str