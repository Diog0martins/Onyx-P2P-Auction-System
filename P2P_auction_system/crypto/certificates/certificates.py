import json
import datetime
from cryptography import x509
from design.ui import UI
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
    """
    Decodes a Base64-encoded PEM CSR, loads it, and cryptographically verifies its signature.
    """
    # Decode the Base64 input to obtain the raw PEM byte string
    csr_pem = b64d(csr_pem_b64)

    # Parse the PEM data into a cryptography CSR object
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
    """
    Generates a PEM-encoded X.509 Certificate Signing Request (CSR) with a custom metadata extension.
    """
    
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
    # Sign the CSR. The builder automatically extracts the public key info from the private_key provided here.
    csr = csr_builder.sign(
        private_key,
        hashes.SHA256()
    )

    return csr.public_bytes(serialization.Encoding.PEM)


def make_x509_certificate(csr: x509.CertificateSigningRequest,
                          ca_sk: rsa.RSAPrivateKey,
                          ca_subject_name: str = "Auction CA") -> bytes:
    
    """
    Issues a new X.509 certificate based on a validated CSR, signed by the provided CA private key.
    """

    # Extract the subject (identity) directly from the CSR to preserve the requested identity
    subject = csr.subject

    # Create the Issuer's Distinguished Name (DN) object from the string argument
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
        # Add BasicConstraints extension:
        # ca=False indicates this is an "end-entity" certificate (it cannot issue other certificates).
        # critical=True means verifiers must reject the cert if they don't understand this extension.
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )
        # Sign the final certificate structure using the CA's private key to establish the chain of trust
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
    """
    Decodes a Base64-encoded PEM certificate and verifies its signature against a trusted CA public key.
    """

    # Decode the Base64 input to get the raw PEM bytes
    cert_pem = b64d(cert_pem_b64)

    # Load the certificate object from the PEM data
    cert = x509.load_pem_x509_certificate(cert_pem)

    try:
        # Cryptographically verify that the certificate was signed by the CA.
        # This checks the signature against the "TBS" (To-Be-Signed) part of the certificate.
        ca_pub.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm
        )
        return True
    except InvalidSignature:
        # Verification failed: the signature does not match the content or the key
        return False


def inspect_certificate(cert_raw):
    """
    Parses and displays key details of an X.509 certificate to the console.
    
    Args:
        cert_raw (bytes | x509.Certificate): The certificate to inspect. Can be provided 
                                             as raw PEM-encoded bytes or an already loaded object.
    """
    # 1. Handle input types: convert PEM bytes to an Object if needed
    if isinstance(cert_raw, bytes):
        try:
            # Attempt to parse raw bytes into a structural x509 object
            cert = x509.load_pem_x509_certificate(cert_raw)
        except Exception:
            # Handle parsing errors (e.g., malformed PEM data) using the external UI handler
            UI.error("   [!] Invalid Certificate Format")
            return
    else:
        # Assume input is already a valid x509.Certificate object
        cert = cert_raw
    print()
    print("         " + "="*35)
    
    # 2. Extract Common Name (CN) specifically for readability
    # The CN is the most common human-readable identifier (e.g., "John Doe" or "example.com")
    try:
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except IndexError:
        # Fallback if the certificate subject does not contain a Common Name attribute
        subject_cn = "No Common Name"

    print(f"         Subject CN:   {subject_cn}")
    
    # 3. Print Full Subject and Issuer strings
    # rfc4514_string() converts the Distinguished Name (DN) object into a standard string format (e.g., "CN=User,O=Company")
    subj_str = cert.subject.rfc4514_string()
    print(f"         Full Subject: {subj_str}")
    
    issuer_str = cert.issuer.rfc4514_string()
    print(f"         Issuer:       {issuer_str}")
    
    # 4. Serial Number
    # Displaying in hex is the standard convention for certificate serial numbers
    print(f"         Serial No:    {hex(cert.serial_number)}")

    # 5. Subject Alternative Names (SANs)
    # SANs are an extension used to secure multiple domains, IPs, or emails in a single cert.
    try:
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        print(f"         SANs:         {san_ext.value}")
    except x509.ExtensionNotFound:
        # It is valid for a certificate to not have any Subject Alternative Names
        print("         SANs:         None")

    print("         " + "="*35)
    print()