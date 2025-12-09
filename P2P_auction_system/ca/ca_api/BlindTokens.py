from pydantic import BaseModel

class BlindSignReq(BaseModel):
    """
        Pydantic model representing the request payload for a Blind Signature.

        Attributes:
            uid (str): The unique identifier of the user requesting the signature.
            blinded_token_b64 (str): The blinded hash of the token (Base64 encoded)
                                     that effectively hides the content from the CA.
    """

    uid: str
    blinded_token_b64: str