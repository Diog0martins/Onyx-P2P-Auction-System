import base64
import secrets
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes

class BlindRSACore:
    def __init__(self, ca_pub_pem: bytes):
        self.ca_pub = serialization.load_pem_public_key(ca_pub_pem)
        if not isinstance(self.ca_pub, rsa.RSAPublicKey):
            raise TypeError("A chave da CA não é RSA")
        self.pub_numbers = self.ca_pub.public_numbers()
        self.n = self.pub_numbers.n
        self.e = self.pub_numbers.e

    def _token_id_to_int(self, token_id: str) -> int:
        digest = hashes.Hash(hashes.SHA256())
        digest.update(token_id.encode("utf-8"))
        h = digest.finalize()
        return int.from_bytes(h, byteorder="big") % self.n

    def _modinv(self, a: int, n: int) -> int:
        t, new_t = 0, 1
        r, new_r = n, a
        while new_r != 0:
            q = r // new_r
            t, new_t = new_t, t - q * new_t
            r, new_r = new_r, r - q * new_r
        if r > 1:
            raise ValueError("a não é inversível modulo n")
        if t < 0:
            t = t + n
        return t

    def generate_blinding_factor(self) -> int:
        """Generates a cryptographically secure random r coprime to n."""
        while True:
            r = secrets.randbelow(self.n - 2) + 1
            try:
                pow(r, -1, self.n) # Check invertibility
                return r
            except ValueError:
                continue

    def blind(self, token_id: str, r: Optional[int] = None) -> Tuple[str, int]:
        """
        Blinds the token. 
        If 'r' is provided, it uses it (for verification). 
        If 'r' is None, it generates a new secure one.
        """
        m = self._token_id_to_int(token_id)

        if r is None:
            r = self.generate_blinding_factor()

        # Calculate blinded message: (m * r^e) mod n
        r_e = pow(r, self.e, self.n)
        blinded = (m * r_e) % self.n

        blinded_b64 = base64.b64encode(
            blinded.to_bytes((self.n.bit_length() + 7) // 8, "big")
        ).decode("ascii")
        
        return blinded_b64, r

    def unblind(self, blind_sig_b64: str, r: int) -> str:
        s_blinded = int.from_bytes(base64.b64decode(blind_sig_b64), "big")
        r_inv = self._modinv(r, self.n)
        s = (s_blinded * r_inv) % self.n
        sig_bytes = s.to_bytes((self.n.bit_length() + 7) // 8, byteorder="big")
        return base64.b64encode(sig_bytes).decode("ascii")

    def verify(self, token_id: str, token_sig_b64: str) -> bool:
        m = self._token_id_to_int(token_id)
        sig_bytes = base64.b64decode(token_sig_b64)
        s = int.from_bytes(sig_bytes, byteorder="big")
        m_check = pow(s, self.e, self.n)
        return m_check == m