import json
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from crypto.encoding.b64 import b64d


# Still useful for signing internal metadata (not X.509)
def canonical_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ------------------------------
# 1. Verify a CSR (real X.509)
# ------------------------------
def verify_csr(csr_pem_b64: str) -> x509.CertificateSigningRequest:
    csr_pem = b64d(csr_pem_b64)

    csr = x509.load_pem_x509_csr(csr_pem)

    # Verify CSR signature (cryptography does this internally)
    try:
        csr.public_key().verify(
            csr.signature,
            csr.tbs_certrequest_bytes,
            padding.PKCS1v15(),
            csr.signature_hash_algorithm
        )
    except Exception:
        raise ValueError("Invalid CSR signature")

    return csr


# ----------------------------------------
# 2. CA creates and signs an X.509 cert
# ----------------------------------------

def create_x509_csr(private_key: rsa.RSAPrivateKey,
                    public_key: rsa.RSAPublicKey,
                    common_name: str,
                    meta: dict) -> bytes:
    
    # Convert meta into extension JSON text
    meta_json = json.dumps(meta).encode()

    csr_builder = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]))
        .add_extension(
            x509.UnrecognizedExtension(
                oid=x509.ObjectIdentifier("1.3.6.1.4.1.99999.1"),  # your custom OID
                value=meta_json
            ),
            critical=False
        )
    )

    csr = csr_builder.sign(
        private_key,
        hashes.SHA256()
    )

    return csr.public_bytes(serialization.Encoding.PEM)


def make_x509_certificate(csr: x509.CertificateSigningRequest,
                          ca_sk: rsa.RSAPrivateKey,
                          ca_subject_name: str = "Auction CA") -> bytes:

    subject = csr.subject

    ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, ca_subject_name)
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=180))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )
        .sign(
            private_key=ca_sk,
            algorithm=hashes.SHA256()
        )
    )

    return cert.public_bytes(serialization.Encoding.PEM)


# ----------------------------------------------------
# 3. Verify certificate signature (CA-side or client)
# ----------------------------------------------------
def verify_certificate(cert_pem_b64: str, ca_pub: rsa.RSAPublicKey) -> bool:
    cert_pem = b64d(cert_pem_b64)
    cert = x509.load_pem_x509_certificate(cert_pem)

    try:
        ca_pub.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm
        )
        return True
    except InvalidSignature:
        return False
