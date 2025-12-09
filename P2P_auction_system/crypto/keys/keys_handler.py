from crypto.keys.keys_crypto import generate_key_pair, load_private_and_public_key

def prepare_key_pair_generation(user_path):
    """
    Ensures that a valid RSA key pair exists in the specified directory.
    
    If keys already exist, they are loaded. If not, a new pair is generated, 
    saved to disk, and then loaded. This ensures the user has a persistent identity.

    Args:
        user_path (pathlib.Path): The directory path object where keys should be stored.

    Returns:
        tuple: A tuple containing (private_key_object, public_key_object).
    """
    
    # Define standard filenames for the key pair using pathlib syntax
    prv_path = user_path / "private_key.pem"
    pub_path = user_path / "public_key.pem"

    # Check if both keys already exist to prevent overwriting an existing identity
    if prv_path.exists() and pub_path.exists():
        return load_private_and_public_key(prv_path, pub_path)

    # If missing, generate a new 2048-bit RSA key pair (PEM encoded bytes)
    private_pem, public_pem = generate_key_pair()
    
    # Ensure the target directory exists. 
    # parents=True allows creating nested directories (e.g., "users/bob/keys")
    user_path.mkdir(parents=True, exist_ok=True)
    
    # Write the raw PEM bytes to disk
    prv_path.write_bytes(private_pem)
    pub_path.write_bytes(public_pem)

    # Load and return the newly created key objects
    return load_private_and_public_key(prv_path, pub_path)