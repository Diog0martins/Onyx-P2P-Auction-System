# 🗓️ Four-Week Deliverables Plan

---

## **Week 1 – Foundation: Basic CA and Host setup**

### 🎯 Goal

Have a **running CA service** and **client host nodes** that can register, obtain keys/tokens, and communicate with basic commands.

---

### **Task 1: CA Service (Basic Identity Authority)**

**Owner:** Member A
**Deliverable:** `ca_service.py`

**Key points:**

* Flask / aiohttp / FastAPI simple HTTP service.
* On `POST /register`: generate an Ed25519 key pair for the user and return certificate signed by CA.
* On `POST /tokens`: issue dummy tokens (random UUIDs for now, no cryptography yet).
* Keep a small SQLite DB of registered users and how many tokens they’ve received.
* Test that multiple hosts can connect and get keys.

---

### **Task 2: Host Node (Client Skeleton)**

**Owner:** Member B
**Deliverable:** `host_node.py`

**Key points:**

* Command-line interface (CLI) that allows:

  * `/register` → connects to CA and retrieves certificate and tokens.
  * `/status` → shows registered info.
  * `/exit` → closes cleanly.
* Store credentials locally (in `~/.auction_node/` folder).
* Prepare structure for commands to come (like `/bid`, `/auction`, etc.).
* Simple network connection test (ping CA).

---

### **Task 3: Project Structure & Networking Skeleton**

**Owner:** Member C
**Deliverable:** `network.py`, `config.py`

**Key points:**

* Set up local P2P stub using `asyncio` and TCP sockets or `websockets`.
* Implement simple peer discovery (hard-coded IP list or multicast).
* Build message format (JSON) with standard fields:

  ```json
  { "type": "message_type", "sender": "id", "payload": {...} }
  ```
* Unit test basic message passing between 2–3 nodes.

---

✅ **End of Week 1 Outcome:**

* You can start CA and two hosts.
* Hosts can register, get keys/tokens, and talk to each other with plain text messages.
* Tokens are dummy; crypto not yet applied.
* Folder structure and communication base ready.

---

## **Week 2 – Cryptographic Layer**

### 🎯 Goal

Implement the **real cryptographic logic** for keys and tokens and integrate it into CA ↔ Host workflow.

---

### **Task 1: Implement RSA Blind Signature in CA**

**Owner:** Member A
**Deliverable:** Update `ca_service.py` to `ca_crypto.py`

**Key points:**

* Generate CA RSA key pair.
* Implement `sign_blind_token()` endpoint: accepts blinded message and returns blind signature.
* Store user token count (limit issuance).
* Provide CA public key to clients.
* Add verification route `/verify_token` for debugging.

---

### **Task 2: Host Token Cryptography**

**Owner:** Member B
**Deliverable:** `token_manager.py`

**Key points:**

* Implement client-side RSA blind-signing functions:

  * `blind_token()`, `unblind_token()`, `verify_token()`.
* Integrate into `/request_tokens` CLI command.
* Save tokens locally (`tokens.json`).
* Test by verifying CA signatures locally.
* Tokens remain unused for now.

---

### **Task 3: Basic Ledger Structure**

**Owner:** Member C
**Deliverable:** `ledger.py`

**Key points:**

* Design local append-only ledger (SQLite or JSON file).
* Schema: `height, prev_hash, events[], block_hash`.
* Implement `add_event()`, `verify_chain()`.
* Support event types: `"register"`, `"token_issued"`, `"message"`.
* Simple test to append events and verify chain integrity.

---

✅ **End of Week 2 Outcome:**

* Real cryptographic token issuance working end-to-end (CA + host).
* Each node stores valid CA-signed tokens locally.
* Simple ledger class implemented for recording events.
* All components tested independently.

---

## **Week 3 – P2P Consensus + Auction Logic**

### 🎯 Goal

Integrate network, ledger, and crypto into a basic **auction + bid** process with **PoS-BFT consensus** on blocks.

---

### **Task 1: PoS-BFT Consensus Skeleton**

**Owner:** Member A
**Deliverable:** `consensus.py`

**Key points:**

* Implement simple Tendermint-like flow:

  * Block proposal → Prevote → Precommit → Commit.
  * Majority (≥2/3 validators) = block final.
* Use Ed25519 keys for validator signatures.
* Store validator list in config (`validators.json`).
* Integrate ledger commit.
* Test by proposing dummy blocks and reaching agreement.

---

### **Task 2: Auction + Bid Commands**

**Owner:** Member B
**Deliverable:** `auction_manager.py`

**Key points:**

* `/create_auction item price` → creates auction event using one token.
* `/bid auction_id amount` → broadcasts bid event using another token.
* Verify token validity and mark as “used” in ledger.
* Record all actions as ledger events (no winner logic yet).
* Include cryptographic signing with Ed25519 ephemeral keys.
* Add console printouts of bids (for demo clarity).

---

### **Task 3: P2P Integration**

**Owner:** Member C
**Deliverable:** Update `network.py`

**Key points:**

* Combine network + consensus + ledger:

  * Broadcasts proposals and votes via gossip.
  * Relays auction and bid events to peers.
* Handle message types: `"proposal"`, `"vote"`, `"auction"`, `"bid"`.
* Ensure each peer updates its ledger consistently after consensus.

---

✅ **End of Week 3 Outcome:**

* Auctions and bids can be created and recorded in all peers’ ledgers via PoS-BFT consensus.
* Token usage verified.
* Bids are public values; bidder identities remain hidden.
* Full basic demo of decentralized auction flow (without identity reveal yet).

---

## **Week 4 – Winner Selection & Identity Reveal**

### 🎯 Goal

Implement **auction closing**, **winner reveal protocol**, and final polish (testing & docs).

---

### **Task 1: Winner Determination & Reveal**

**Owner:** Member A
**Deliverable:** Update `auction_manager.py`

**Key points:**

* Implement logic to close auction after time or manual trigger.
* Determine highest bid from ledger.
* Notify winning token ID.
* Implement winner’s private identity reveal:

  * Winner encrypts `{cert, proof, token_id}` to seller’s `R_pub` using X25519+AEAD.
  * Seller decrypts and verifies ownership.

---

### **Task 2: Security & Verification Tests**

**Owner:** Member B
**Deliverable:** `test_security.py`

**Key points:**

* Test:

  * Double-token usage rejection.
  * Invalid signature detection.
  * Ledger tampering (hash mismatch).
  * Fake CA rejection.
* Unit tests for blind signature correctness and reveal verification.

---

### **Task 3: Integration, CLI & Demo Prep**

**Owner:** Member C
**Deliverable:** `main.py`, Demo script

**Key points:**

* Integrate all modules into unified CLI or menu:

  * `/register`, `/request_tokens`, `/create_auction`, `/bid`, `/close_auction`.
* Add simple UI logs (console messages).
* Prepare demo scenario:

  * Start CA, start 3–4 nodes, run one auction from start to finish.
  * Show consensus logs and winner identity reveal privately.
* Final polish (comments, README, architecture diagram).

---

✅ **End of Week 4 Outcome:**

* Fully functional P2P auction demo:

  * CA issues keys and blind-signed tokens.
  * Nodes bid anonymously with tokens.
  * Bids recorded via PoS-BFT consensus.
  * Winner and seller reveal identities privately.
  * Tested and documented.

---

# ✅ Summary Table

| Week  | Theme        | Member A          | Member B          | Member C            |
| ----- | ------------ | ----------------- | ----------------- | ------------------- |
| **1** | Setup        | CA Service        | Host Node         | Networking Skeleton |
| **2** | Crypto       | RSA Blind Sign CA | Token Manager     | Ledger              |
| **3** | Core Logic   | PoS-BFT Consensus | Auction/Bid Logic | Network Integration |
| **4** | Finalization | Winner Reveal     | Security Testing  | CLI & Demo          |

---

This plan keeps all three members active every week, with minimal dependency blocking.
Each week ends with something *runnable and testable* — so you always have a working prototype at every stage.

Would you like me to now produce a **file/folder structure layout** (showing how the Python modules fit together across these tasks)? It’ll help you organize your repo cleanly from day one.

