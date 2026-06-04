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
    bilingual: bool = False
    voice: bool = False
    history: list[dict] = field(default_factory=list)  # [{"role": ..., "content": ...}, ...]

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "language": self.language,
            "scene": self.scene,
            "bilingual": self.bilingual,
            "voice": self.voice,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        return cls(
            active=data.get("active", False),
            language=data.get("language", "english"),
            scene=data.get("scene", "daily"),
            bilingual=data.get("bilingual", False),
            voice=data.get("voice", False),
            history=data.get("history", []),
        )


class SessionManager:
    """管理所有用户的会话状态，支持持久化"""

    def __init__(self, data_dir: str, max_history_rounds: int = 10):
        self.storage = JsonStorage(str(Path(data_dir) / "sessions.json"))
        # 防御性夹取，避免 0/负数导致 history[-0:] 不截断的隐患
        try:
            self.max_history_rounds = max(1, min(50, int(max_history_rounds)))
        except (TypeError, ValueError):
            self.max_history_rounds = 10
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

    def peek_session(self, user_id: str) -> Session | None:
        """只读获取会话，不存在时返回 None（不创建），用于高频消息路径。"""
        return self._sessions.get(user_id)

    def start_session(
        self, user_id: str, language: str, scene: str, voice: bool = False
    ) -> Session:
        session = self.get_session(user_id)
        session.active = True
        session.language = language
        session.scene = scene
        session.voice = voice
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

    def toggle_bilingual(self, user_id: str) -> bool:
        session = self.get_session(user_id)
        session.bilingual = not session.bilingual
        self._save()
        return session.bilingual

    def toggle_voice(self, user_id: str) -> bool:
        session = self.get_session(user_id)
        session.voice = not session.voice
        self._save()
        return session.voice

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
