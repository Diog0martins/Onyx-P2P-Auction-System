import logging
import json
import time
from datetime import datetime

# Configure a dedicated security logger
sec_logger = logging.getLogger("PeerSecurity")
sec_logger.setLevel(logging.INFO)
handler = logging.FileHandler("peer_security.log")
handler.setFormatter(logging.Formatter('%(message)s')) # We will format as JSON string manually
sec_logger.addHandler(handler)

# In-memory metrics tracker
metrics = {
    "validation_fail_rate": 0,
    "block_hash_mismatch": 0,
    "token_reuse_rate": 0,
    "msg_processing_latency": []
}

def log_security_event(event_type, status, reason="", auction_id=None, token_id=None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "auction_id": auction_id,
        "token_id": token_id,
        "status": status,
        "reason": reason
    }
    # Log to file
    sec_logger.info(json.dumps(log_entry))
    
    # Update Metrics based on event
    if status == "failure":
        if event_type in ["invalid_signature", "timestamp_invalid", "decryption_error"]:
            metrics["validation_fail_rate"] += 1
        elif event_type == "token_reuse_detected":
            metrics["token_reuse_rate"] += 1
        elif event_type == "ledger_divergence":
            metrics["block_hash_mismatch"] += 1

def record_latency(start_time):
    latency_ms = (time.time() - start_time) * 1000
    metrics["msg_processing_latency"].append(latency_ms)
    # Keep only the last 100 for a rolling average
    if len(metrics["msg_processing_latency"]) > 100:
        metrics["msg_processing_latency"].pop(0)
