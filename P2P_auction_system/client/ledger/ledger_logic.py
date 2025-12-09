import hashlib
import json
from datetime import datetime


# ============= Utility Functions =============

def compute_hash(block):
    """
    Computes the SHA-256 hash of a block by serializing it to a JSON string.
    Removes 'block_hash' from the dictionary before hashing to ensure consistency.
    """
    temp = dict(block)
    temp.pop("block_hash", None)
    block_str = json.dumps(temp, sort_keys=True).encode()
    return hashlib.sha256(block_str).hexdigest()


# ============= Ledger Core =============

class Ledger:
    def __init__(self):
        self.chain = []
        self.current_actions = []
        self.max_actions = 1
        self.create_ledger()

    # Network Serialization Utils
    def to_dict(self):
        """
        Serializes the Ledger object into a dictionary for network transmission.
        """
        return {
            "chain": self.chain,
            "current_actions": self.current_actions,
            "max_actions": self.max_actions
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Reconstructs a Ledger object from a received dictionary.
        """
        obj = cls()
        obj.chain = data["chain"]
        obj.current_actions = data["current_actions"]
        obj.max_actions = data["max_actions"]
        return obj

    def create_ledger(self):
        """
        Initializes the blockchain with a hardcoded Genesis Block.
        """
        genesis_block = {
            "height": 0,
            "prev_hash": "0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "events": [
                {"type": "genesis", "description": "Ledger initialized"}
            ],
            "block_hash": None,
        }
        
        genesis_block["block_hash"] = compute_hash(genesis_block)
        self.chain.append(genesis_block)
    
    def add_action(self, action):
        """
        Adds a new event) to the block.
        If the pool size reaches 'max_actions', it automatically triggers block creation.
        Returns 1 if a block was created, 0 otherwise.
        """
        self.current_actions.append(action)
        
        if len(self.current_actions) == self.max_actions:
            self.finish_block()
            return 1
        
        return 0

    def finish_block(self):
        """
        Finalizes the current block by calculating its hash and linking it to the 
        previous block in the chain. Clears the pending action pool.
        """
        if not self.current_actions:
            raise RuntimeError("Cannot finish block: no actions added.")

        prev_block = self.chain[-1]

        new_block = {
            "height": prev_block["height"] + 1,
            "prev_hash": prev_block["block_hash"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "events": self.current_actions.copy(),
            "block_hash": None,
        }

        new_block["block_hash"] = compute_hash(new_block)

        # Commit to Chain
        self.chain.append(new_block)
        self.current_actions = []

        return new_block

    def verify_chain(self):
        """
        Iterates through the entire blockchain to validate cryptographic integrity.
        Checks block continuity (height), hash linkage (prev_hash), and data integrity (hash recalculation).
        """
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            prev = self.chain[i - 1]

            # Height check
            if block["height"] != prev["height"] + 1:
                return False, f"Height mismatch at block {block['height']}"

            # Prev hash check
            if block["prev_hash"] != prev["block_hash"]:
                return False, f"Prev_hash mismatch at block {block['height']}"

            # Recalculate block hash
            recalculated = compute_hash(block)
            if recalculated != block["block_hash"]:
                return False, f"Invalid block_hash at block {block['height']}"

        return True, "Chain is valid"

    def find_auction_public_key(self, auction_id):
        """
        Searches the chain for the 'auction' creation event of a specific ID 
        and returns the public key associated with it (used for reveal encryption).
        """
        for block in self.chain:
            for action in block.get("events", []):
                if action.get("type") == "auction":
                    if action.get("id") == auction_id:
                        return action.get("public_key")

        return None
    
    def find_token_signature(self, token_id):
        """
        Scans the chain to find the CA signature associated with a specific token ID.
        Used for verification during the identity reveal phase.
        """
        for block in self.chain:
            for action in block.get("events", []):
                
                # Support both naming conventions depending on message type
                token_info = action.get("token")
                
                if not token_info:
                    continue

                if token_info.get("token_id") == token_id:
                    return token_info.get("token_sig")

        return None


    # ============= File I/O =============

    def save_to_file(self, path):
        """
        Persists the current blockchain state to a JSON file.
        """
        with open(path, "w") as f:
            json.dump(self.chain, f, indent=2)

    def load_from_file(path):
        """
        Static method to load a Ledger object from a JSON file.
        Returns a fresh Ledger if the file is empty or corrupted.
        """
        import os

        # If file exists but is empty -> new ledger
        if os.path.getsize(path) == 0:
            return None

        # Try reading JSON
        try:
            with open(path, "r") as f:
                chain = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        # Create ledger object without running __init__ to avoid overwriting state
        ledger = Ledger.__new__(Ledger)
        ledger.chain = chain
        ledger.current_actions = []
        ledger.max_actions = 1

        return ledger
    
    def token_used(self, token):
        """
        Checks if a specific token ID has already been recorded in the blockchain,
        effectively preventing Double-Spending.
        """
        for block in self.chain:
            for action in block.get("events", []):
                if not action.get("type") == "genesis":
                    if action.get("token").get("token_id") == token:
                        return True
        return False


# ============= Ledger Helpers =============

def validate_block(block, prev_block):
    """
    Validates a single incoming block structure against the local previous block.
    """
    if block["height"] != prev_block["height"] + 1:
        return False, "Height mismatch"

    if block["prev_hash"] != prev_block["block_hash"]:
        return False, "Prev_hash mismatch"

    if compute_hash(block) != block["block_hash"]:
        return False, "Hash mismatch"

    if len(block.get("events", [])) > 3:
        return False, "Too many events"

    return True, "OK"


def receive_block(ledger, block):
    """
    Attempts to append a received block to the local ledger after validation.
    """
    prev_block = ledger.chain[-1]
    ok, msg = validate_block(block, prev_block)

    if not ok:
        return False, msg

    ledger.chain.append(block)
    return True, "Block accepted"


def get_latest_block(ledger):
    """
    Returns the tip of the blockchain.
    """
    return ledger.chain[-1]


def compare_chains(local_chain, remote_chain):
    """
    Implements the Longest Chain Rule for simple consensus.
    Returns 'remote' if the incoming chain is longer, otherwise 'local'.
    """
    if len(remote_chain) > len(local_chain):
        return "remote"
    return "local"