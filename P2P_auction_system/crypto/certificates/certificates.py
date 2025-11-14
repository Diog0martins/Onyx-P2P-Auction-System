import json
from typing import Optional

from crypto.encoding.b64 import b64e, b64d
from ca.ca_utils.time import now_iso, iso_in_days

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

from cryptography.exceptions import InvalidSignature


# Converte dicionário Python em JSON
def canonical_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# Create a certificate 
def make_certificate(uid: str, user_pub: str, meta: Optional[dict], sk: rsa.RSAPrivateKey) -> tuple[dict, str]:
    
    cert = {
        "uid": uid,
        "user_pub": user_pub,
        "issued_at": now_iso(),
        "expiry": iso_in_days(180),
        "meta": meta or {}
    }

    sig = sk.sign(
        canonical_bytes(cert),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return cert, b64e(sig)


# Verify a certificate
def verify_certificate(cert: dict, cert_sig_b64: str, vk: rsa.RSAPublicKey) -> bool:
    try:
        vk.verify(
            b64d(cert_sig_b64),
            canonical_bytes(cert),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        return False