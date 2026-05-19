"""会话状态管理"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .storage import JsonStorage


@dataclass
class Session:
    """单个用户的口语练习会话"""

    active: bool = False
    language: str = "english"
    scene: str = "daily"
    history: list[dict] = field(default_factory=list)  # [{"role": ..., "content": ...}, ...]

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "language": self.language,
            "scene": self.scene,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        return cls(
            active=data.get("active", False),
            language=data.get("language", "english"),
            scene=data.get("scene", "daily"),
            history=data.get("history", []),
        )


class SessionManager:
    """管理所有用户的会话状态，支持持久化"""

    def __init__(self, data_dir: str, max_history_rounds: int = 10):
        self.storage = JsonStorage(str(Path(data_dir) / "sessions.json"))
        self.max_history_rounds = max_history_rounds
        self._sessions: dict[str, Session] = {}
        self._load()

    def _load(self):
        raw = self.storage.load()
        for uid, data in raw.items():
            self._sessions[uid] = Session.from_dict(data)

    def _save(self):
        data = {uid: s.to_dict() for uid, s in self._sessions.items()}
        self.storage.save(data)

    def get_session(self, user_id: str) -> Session:
        if user_id not in self._sessions:
            self._sessions[user_id] = Session()
        return self._sessions[user_id]

    def start_session(self, user_id: str, language: str, scene: str) -> Session:
        session = self.get_session(user_id)
        session.active = True
        session.language = language
        session.scene = scene
        session.history = []
        self._save()
        return session

    def stop_session(self, user_id: str) -> Session:
        session = self.get_session(user_id)
        session.active = False
        session.history = []
        self._save()
        return session

    def switch_language(self, user_id: str, language: str) -> Session:
        session = self.get_session(user_id)
        session.language = language
        session.history = []
        self._save()
        return session

    def switch_scene(self, user_id: str, scene: str) -> Session:
        session = self.get_session(user_id)
        session.scene = scene
        session.history = []
        self._save()
        return session

    def reset_history(self, user_id: str) -> Session:
        session = self.get_session(user_id)
        session.history = []
        self._save()
        return session

    def add_message(self, user_id: str, role: str, content: str):
        session = self.get_session(user_id)
        session.history.append({"role": role, "content": content})
        # 保留最近 N 轮（每轮 2 条：user + assistant）
        max_messages = self.max_history_rounds * 2
        if len(session.history) > max_messages:
            session.history = session.history[-max_messages:]
        self._save()

    def get_history(self, user_id: str) -> list[dict]:
        return self.get_session(user_id).history
