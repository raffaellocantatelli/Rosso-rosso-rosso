import os

NODE_ID = os.environ.get("R3_NODE_ID", "node-a")
API_TOKEN = os.environ.get("R3_API_TOKEN", "changeme")
DATA_DIR = os.environ.get("R3_DATA_DIR", "data")
PEERS = [p.strip().rstrip("/") for p in os.environ.get("R3_PEERS", "").split(",") if p.strip()]
SYNC_INTERVAL = int(os.environ.get("R3_SYNC_INTERVAL", "300"))
INTEGRITY_INTERVAL = int(os.environ.get("R3_INTEGRITY_INTERVAL", "3600"))
