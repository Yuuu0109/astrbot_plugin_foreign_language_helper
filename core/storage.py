"""JSON 持久化存储"""

import json
import os
import threading
from astrbot.api import logger


class JsonStorage:
    """简单的 JSON 文件持久化存储"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def load(self) -> dict:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load storage file {self.file_path}: {e}")
            return {}

    def save(self, data: dict):
        """原子写入：先写临时文件，再替换正式文件，避免写入中断损坏数据。"""
        tmp_path = self.file_path + ".tmp"
        with self._lock:
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self.file_path)
            except OSError as e:
                logger.error(f"Failed to save storage file {self.file_path}: {e}")
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
