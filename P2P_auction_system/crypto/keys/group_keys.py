from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from crypto.encoding.b64 import b64d, b64e

def find_my_new_key(encrypted_keys_list, private_key):

    print(f"[*] Attempting to decrypt {len(encrypted_keys_list)} keys...")

    for i, enc_b64 in enumerate(encrypted_keys_list):
        try:
            ciphertext = b64d(enc_b64)
            
            plaintext_bytes = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            new_group_key = b64e(plaintext_bytes)
            
            print(f"[+] Success! Key found at index {i}")
            return plaintext_bytes
            
        except Exception:
            continue
            
    print("[-] Could not decrypt any key in the list.")
    return None