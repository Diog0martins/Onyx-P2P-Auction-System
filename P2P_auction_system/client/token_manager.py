import json
import base64
import secrets
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes

CA_URL = "http://127.0.0.1:8443"

class TokenManager:
    def __init__(self, config_name: str, ca_pub_pem: bytes, uid: str):
        self.config_dir = Path("config") / config_name
        self.wallet_path = self.config_dir / "token_wallet.json"
        self.uid = uid
        self.ca_pub = serialization.load_pem_public_key(ca_pub_pem)
        if not isinstance(self.ca_pub, rsa.RSAPublicKey):
            raise TypeError("A chave da CA não é RSA")


    def _token_id_to_int(self, token_id: str, n: int) -> int:
        digest = hashes.Hash(hashes.SHA256())
        digest.update(token_id.encode("utf-8"))
        h = digest.finalize()
        m = int.from_bytes(h, byteorder="big")
        return m % n

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

    def blind_token(self, token_id: str) -> Tuple[str, int]:
        pub_numbers = self.ca_pub.public_numbers()
        n = pub_numbers.n
        e = pub_numbers.e
        m = self._token_id_to_int(token_id, n)

        while True:
            r = secrets.randbelow(n - 2) + 1
            try:
                pow(r, -1, n)
                break
            except ValueError:
                continue

        r_e = pow(r, e, n)
        blinded = (m * r_e) % n

        blinded_b64 = base64.b64encode(blinded.to_bytes((n.bit_length() + 7) // 8, "big")).decode("ascii")
        return blinded_b64, r

    def unblind_signature(self, blind_sig_b64: str, r: int) -> str:
        pub_numbers = self.ca_pub.public_numbers()
        n = pub_numbers.n
        s_blinded = int.from_bytes(base64.b64decode(blind_sig_b64), "big")
        r_inv = self._modinv(r, n)
        s = (s_blinded * r_inv) % n
        sig_bytes = s.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
        return base64.b64encode(sig_bytes).decode("ascii")

    def verify_token(self, token_id: str, token_sig_b64: str) -> bool:
        pub_numbers = self.ca_pub.public_numbers()
        n = pub_numbers.n
        e = pub_numbers.e
        m = self._token_id_to_int(token_id, n)
        sig_bytes = base64.b64decode(token_sig_b64)
        s = int.from_bytes(sig_bytes, byteorder="big")
        m_check = pow(s, e, n)
        return m_check == m


    def _save_to_wallet(self, token_id: str, blinded_token: str, r: int, token_sig: str):
        wallet = []
        if self.wallet_path.exists():
            try:
                with self.wallet_path.open("r") as f:
                    wallet = json.load(f)
            except:
                pass

        entry = {
            "token_id": token_id,
            "blinded_token_b64": blinded_token,
            "blinding_factor_r": str(r),
            "token_signature_b64": token_sig,
            "timestamp": datetime.now().isoformat(),
        }

        wallet.append(entry)

        self.config_dir.mkdir(parents=True, exist_ok=True)
        with self.wallet_path.open("w") as f:
            json.dump(wallet, f, indent=4)


    def get_token(self) -> Dict:
        print("[TokenManager] A gerar novo token para a transação...")

        try:
            payload_quota = {"uid": self.uid, "count": 1}
            r_quota = requests.post(f"{CA_URL}/tokens", json=payload_quota, timeout=5)
            r_quota.raise_for_status()
        except Exception as e:
            print(f"[!] Erro ao contactar CA (/tokens): {e}")
            raise e

        token_id = secrets.token_hex(16)
        blinded_b64, r = self.blind_token(token_id)

        req_body = {
            "uid": self.uid,
            "blinded_token_b64": blinded_b64
        }

        try:
            resp = requests.post(f"{CA_URL}/blind_sign", json=req_body, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            blind_sig_b64 = data["blind_signature_b64"]

            token_sig_b64 = self.unblind_signature(blind_sig_b64, r)

            if not self.verify_token(token_id, token_sig_b64):
                raise Exception("CA devolveu uma assinatura inválida!")

            self._save_to_wallet(token_id, blinded_b64, r, token_sig_b64)

            print(f"[TokenManager] Token guardado na carteira e pronto a enviar.")

            return {
                "token_id": token_id,
                "token_sig": token_sig_b64
            }

        except Exception as e:
            print(f"[!] Falha no processo de Blind Sign: {e}")
            raise e