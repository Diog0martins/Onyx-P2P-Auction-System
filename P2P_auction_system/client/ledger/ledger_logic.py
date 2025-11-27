import hashlib
import json
from datetime import datetime

# -------------------------------------------------------------
# Utility
# -------------------------------------------------------------

def compute_hash(block):
    temp = dict(block)
    temp.pop("block_hash", None)
    block_str = json.dumps(temp, sort_keys=True).encode()
    return hashlib.sha256(block_str).hexdigest()


# -------------------------------------------------------------
# Ledger Core
# -------------------------------------------------------------

class Ledger:
    def __init__(self):
        self.chain = []
        self.current_actions = []
        self.max_actions = 3
        self.create_ledger()

    # Send over the network utils -----
    def to_dict(self):
        return {
            "chain": self.chain,
            "current_actions": self.current_actions,
            "max_actions": self.max_actions
        }
    
    @classmethod
    def from_dict(cls, data):
        obj = cls()
        obj.chain = data["chain"]
        obj.current_actions = data["current_actions"]
        obj.max_actions = data["max_actions"]
        return obj

    # ---------------------------------------------------------

    def create_ledger(self):
        """Creates a genesis block."""
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

    # ---------------------------------------------------------
    def add_action(self, action):
        self.current_actions.append(action)

        if len(self.current_actions) == self.max_actions:
            self.finish_block()
            return 1
        
        return 0

    # ---------------------------------------------------------
    def finish_block(self):
        """Closes a block, hashes it, and appends it to the chain."""
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

        # Commit
        self.chain.append(new_block)
        self.current_actions = []

        return new_block

    # ---------------------------------------------------------
    def verify_chain(self):
        """Verifies the entire chain for hash correctness and continuity."""

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
    
    # ---------------------------------------------------------
    def save_to_file(self, path):
        """Save the current ledger chain to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.chain, f, indent=2)

    # ---------------------------------------------------------
    def load_from_file(path):
        """Load the ledger from file or create a new one if invalid."""
        import os
        import json

        # If file exists but is empty → new ledger
        if os.path.getsize(path) == 0:
            return None

        # Try reading JSON
        try:
            with open(path, "r") as f:
                chain = json.load(f)
        except (json.JSONDecodeError, OSError):
            # If file is corrupted, fallback to a fresh ledger
            return None

        # Create ledger object without running __init__
        ledger = Ledger.__new__(Ledger)
        ledger.chain = chain
        ledger.current_actions = []
        ledger.max_actions = 3

        return ledger
    
    def token_used(self, token):
        for block in self.chain:
            for action in block.get("events", []):
                if not action.get("type") == "genesis":
                    if action.get("token").get("token_id") == token:
                        return True
        return False




# -------------------------------------------------------------
# P2P Support (minimal)
# -------------------------------------------------------------

def validate_block(block, prev_block):
    """Validates a single incoming block before adding it from peers."""
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
    """Append a block from a peer after validating it."""
    prev_block = ledger.chain[-1]
    ok, msg = validate_block(block, prev_block)

    if not ok:
        return False, msg

    ledger.chain.append(block)
    return True, "Block accepted"


def get_latest_block(ledger):
    """Returns the last block in the chain."""
    return ledger.chain[-1]


def compare_chains(local_chain, remote_chain):
    """Simplest consensus rule: choose longer valid chain."""
    if len(remote_chain) > len(local_chain):
        return "remote"
    return "local"
