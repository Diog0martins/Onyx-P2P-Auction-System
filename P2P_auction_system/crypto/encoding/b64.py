import base64

# Codificam base64
def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

# Descodificam base64
def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))