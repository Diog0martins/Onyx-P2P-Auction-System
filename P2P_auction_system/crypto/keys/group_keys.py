from design.ui import UI
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from crypto.encoding.b64 import b64d

def find_my_new_key(encrypted_keys_list, private_key):
    """
    Iterates through a list of encrypted keys, attempting to decrypt each one with the given private key.
    
    This is typically used in multi-recipient systems where a sender encrypts the same symmetric key 
    multiple times (once for each recipient's public key) and bundles them. The recipient must 
    find which encrypted blob belongs to them.

    Args:
        encrypted_keys_list (list): A list of Base64 encoded strings, each representing an encrypted key.
        private_key (rsa.RSAPrivateKey): The private key used to attempt decryption.

    Returns:
        bytes | None: The decrypted raw key bytes if successful, or None if no matching key is found.
    """

    # User Interface log: Notify start of search
    UI.sub_peer("Attempting to decrypt {len(encrypted_keys_list)} keys...")

    # Iterate through every encrypted key in the provided list
    for i, enc_b64 in enumerate(encrypted_keys_list):
        try:
            # Decode Base64 to get raw ciphertext bytes
            ciphertext = b64d(enc_b64)
            
            # Attempt decryption.
            # If 'ciphertext' was not encrypted with the Public Key corresponding to this 'private_key',
            # or if the padding is incorrect, this method will raise an exception (usually ValueError or InvalidKey).
            plaintext_bytes = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # If we reach this line, decryption was successful. We found our key.
            UI.sub_peer("Success! Key found at index {i}")
            return plaintext_bytes
            
        except Exception:
            # Decryption failed for this specific item. 
            # This is expected behavior for items belonging to OTHER recipients.
            # We silently ignore the error and continue to the next item.
            continue
    
    # If the loop finishes without returning, none of the keys could be decrypted.
    UI.sub_error("Could not decrypt any key in the list.")        

    return None