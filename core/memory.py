"""
File-as-Memory: External storage for intermediate results.

Instead of passing raw content through the LangGraph state (which would
blow up the context window), agents write intermediate results here
and only pass compressed summaries in the state.
"""
import json
import os
from datetime import datetime
from config import MEMORY_DIR


def new_run_id() -> str:
    """一次研究（所有迭代轮次）共用一个 run_id，对应 outputs/memory/<run_id>/ 目录。"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class MemoryStore:
    """Simple file-based memory store for agent intermediate results."""
    
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = os.path.join(MEMORY_DIR, self.session_id)
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save(self, key: str, data: dict | list | str) -> str:
        """Save data to file, return the file path."""
        filepath = os.path.join(self.base_dir, f"{key}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
    
    def load(self, key: str) -> dict | list | str | None:
        """Load data from file by key."""
        filepath = os.path.join(self.base_dir, f"{key}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in memory."""
        filepath = os.path.join(self.base_dir, f"{key}.json")
        return os.path.exists(filepath)
    
    def list_keys(self) -> list[str]:
        """List all keys in the current session."""
        keys = []
        for f in os.listdir(self.base_dir):
            if f.endswith(".json"):
                keys.append(f[:-5])
        return keys
