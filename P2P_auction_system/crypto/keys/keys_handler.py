from crypto.keys.keys_crypto import generate_key_pair, load_private_and_public_key


def prepare_key_pair_generation(user_path):
    
    prv_path = user_path / "private_key.pem"
    pub_path = user_path / "public_key.pem"

    if prv_path.exists() and pub_path.exists():
        return load_private_and_public_key(prv_path, pub_path)

    # Generate new pair
    private_pem, public_pem = generate_key_pair()
    
    # Ensure directory exists
    user_path.mkdir(parents=True, exist_ok=True)
    prv_path.write_bytes(private_pem)
    pub_path.write_bytes(public_pem)

    return load_private_and_public_key(prv_path, pub_path)
