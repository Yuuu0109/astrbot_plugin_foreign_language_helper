"""外语口语助手 - 通过大模型进行外语口语练习"""

import json

from astrbot.api import logger, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.star.star_tools import StarTools

from .core.prompts import (
    LANG_NAMES,
    SCENE_DISPLAY_NAMES,
    build_system_prompt,
)
from .core.session import SessionManager

# 语种别名映射（支持中文/英文输入 -> 内部 key）
LANG_ALIASES = {
    "english": "english",
    "japanese": "japanese",
    "英语": "english",
    "日语": "japanese",
}


def _resolve_language(raw: str) -> str | None:
    """将用户输入的语种名称解析为内部 key，未匹配返回 None。"""
    return LANG_ALIASES.get(raw.lower())


class ForeignLanguageHelper(star.Star):
    """外语口语助手：通过大模型进行英语/日语口语练习，支持多场景切换。
    发送 /lang help 查看帮助。"""

    def __init__(self, context: star.Context, config: dict = None) -> None:
        self.context = context
        self._plugin_config = config or {}

    async def initialize(self):
        cfg = self._plugin_config
        self.default_language = _resolve_language(cfg.get("default_language", "english")) or "english"
        self.default_scene = cfg.get("default_scene", "daily")
        self.max_history_rounds = cfg.get("max_history_rounds", 10)
        self.correction_level = cfg.get("correction_level", "light")
        self.difficulty = cfg.get("difficulty", "intermediate")

        # custom_scenes 存储为 JSON 字符串
        custom_scenes_raw = cfg.get("custom_scenes", "[]")
        if isinstance(custom_scenes_raw, str):
            try:
                self.custom_scenes = json.loads(custom_scenes_raw)
            except json.JSONDecodeError:
                logger.warning("自定义场景 JSON 解析失败，使用空列表")
                self.custom_scenes = []
        else:
            self.custom_scenes = custom_scenes_raw if isinstance(custom_scenes_raw, list) else []

        data_dir = str(StarTools.get_data_dir())
        self.session_mgr = SessionManager(
            data_dir=data_dir,
            max_history_rounds=self.max_history_rounds,
        )

        # 构建自定义场景映射 {name: {display_name, prompt}}
        self._custom_scene_map: dict[str, dict] = {}
        for cs in self.custom_scenes:
            name = cs.get("name", "").strip()
            if name:
                self._custom_scene_map[name] = {
                    "display_name": cs.get("display_name", name),
                    "prompt": cs.get("prompt", ""),
                }

        logger.info("外语口语助手插件已加载")

    # ==================== /lang 命令组 ====================

    @filter.command_group("lang")
    def lang(self):
        """外语口语助手指令组"""

    # ---- /lang start ----
    @lang.command("start")
    async def lang_start(self, event: AstrMessageEvent):
        """开始口语练习会话。用法: /lang start [语种] [场景]
        示例: /lang start 英语 在咖啡馆和朋友聊天"""
        args = event.message_str.strip().split()
        parts = args[2:] if len(args) >= 2 else []

        if len(parts) >= 1:
            language = _resolve_language(parts[0])
            if language is None:
                # 第一个参数不是语种，视为场景描述
                language = self.default_language
                scene = " ".join(parts)
            else:
                scene = " ".join(parts[1:]) if len(parts) >= 2 else self.default_scene
        else:
            language = self.default_language
            scene = self.default_scene

        if not scene:
            scene = self.default_scene

        user_id = event.get_sender_id()
        self.session_mgr.start_session(user_id, language, scene)

        lang_display = LANG_NAMES.get(language, language)
        scene_display = self._get_scene_display_name(scene)
        yield event.plain_result(
            f"口语练习已开始!\n"
            f"语种: {lang_display}\n"
            f"场景: {scene_display}\n"
            f"难度: {self.difficulty}\n"
            f"纠错: {self.correction_level}\n\n"
            f"直接发送消息即可开始对话，发送 /lang stop 结束练习。"
        )

    # ---- /lang stop ----
    @lang.command("stop")
    async def lang_stop(self, event: AstrMessageEvent):
        """结束口语练习会话"""
        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("当前没有进行中的口语练习。")
            return
        self.session_mgr.stop_session(user_id)
        yield event.plain_result("口语练习已结束，对话历史已清除。")

    # ---- /lang lang ----
    @lang.command("lang")
    async def lang_lang(self, event: AstrMessageEvent):
        """切换目标语种。用法: /lang lang <语种>"""
        args = event.message_str.strip().split()
        parts = args[2:] if len(args) >= 2 else []

        if not parts:
            yield event.plain_result(
                f"用法: /lang lang <语种>\n支持: {', '.join(LANG_ALIASES.keys())}"
            )
            return

        language = _resolve_language(parts[0])
        if language is None:
            yield event.plain_result(
                f"不支持的语种: {parts[0]}\n支持: {', '.join(LANG_ALIASES.keys())}"
            )
            return

        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("请先使用 /lang start 开始练习。")
            return

        self.session_mgr.switch_language(user_id, language)
        lang_display = LANG_NAMES.get(language, language)
        yield event.plain_result(f"已切换语种为 {lang_display}，对话历史已重置。")

    # ---- /lang scene ----
    @lang.command("scene")
    async def lang_scene(self, event: AstrMessageEvent):
        """切换对话场景。用法: /lang scene <场景描述>"""
        args = event.message_str.strip().split()
        parts = args[2:] if len(args) >= 2 else []

        if not parts:
            available = self._get_available_scenes()
            yield event.plain_result(
                f"用法: /lang scene <场景描述>\n内置场景: {', '.join(available)}\n也可输入任意场景描述，如: /lang scene 在咖啡馆和朋友聊天"
            )
            return

        scene = " ".join(parts)

        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("请先使用 /lang start 开始练习。")
            return

        self.session_mgr.switch_scene(user_id, scene)
        scene_display = self._get_scene_display_name(scene)
        yield event.plain_result(f"已切换场景为 {scene_display}，对话历史已重置。")

    # ---- /lang switch ----
    @lang.command("switch")
    async def lang_switch(self, event: AstrMessageEvent):
        """同时切换语种和场景。用法: /lang switch <语种> <场景>"""
        args = event.message_str.strip().split()
        parts = args[2:] if len(args) >= 2 else []

        if len(parts) < 2:
            yield event.plain_result("用法: /lang switch <语种> <场景描述>\n示例: /lang switch 日语 在居酒屋点餐")
            return

        language = _resolve_language(parts[0])
        if language is None:
            yield event.plain_result(
                f"不支持的语种: {parts[0]}\n支持: {', '.join(LANG_ALIASES.keys())}"
            )
            return

        scene = " ".join(parts[1:])

        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("请先使用 /lang start 开始练习。")
            return

        self.session_mgr.switch_language(user_id, language)
        self.session_mgr.switch_scene(user_id, scene)

        lang_display = LANG_NAMES.get(language, language)
        scene_display = self._get_scene_display_name(scene)
        yield event.plain_result(
            f"已切换: {lang_display} - {scene_display}，对话历史已重置。"
        )

    # ---- /lang list ----
    @lang.command("list")
    async def lang_list(self, event: AstrMessageEvent):
        """查看可用的语种和场景列表"""
        lines = ["可用语种:"]
        for lang_key, lang_name in LANG_NAMES.items():
            cn_alias = [k for k, v in LANG_ALIASES.items() if v == lang_key and k != lang_key]
            alias_str = f" / {'、'.join(cn_alias)}" if cn_alias else ""
            lines.append(f"  {lang_key}{alias_str} - {lang_name}")

        lines.append("\n内置场景:")
        for scene_key, display_name in SCENE_DISPLAY_NAMES.items():
            lines.append(f"  {scene_key} - {display_name}")

        if self._custom_scene_map:
            lines.append("\n自定义场景:")
            for name, info in self._custom_scene_map.items():
                lines.append(f"  {name} - {info['display_name']}")

        lines.append("\n也可输入任意场景描述，如: /lang start 英语 在咖啡馆和朋友聊天")

        yield event.plain_result("\n".join(lines))

    # ---- /lang status ----
    @lang.command("status")
    async def lang_status(self, event: AstrMessageEvent):
        """查看当前练习状态"""
        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("当前没有进行中的口语练习。\n使用 /lang start 开始。")
            return

        lang_display = LANG_NAMES.get(session.language, session.language)
        scene_display = self._get_scene_display_name(session.scene)
        history_count = len(session.history)
        bilingual_text = "开启" if session.bilingual else "关闭"
        yield event.plain_result(
            f"练习状态:\n"
            f"  语种: {lang_display}\n"
            f"  场景: {scene_display}\n"
            f"  双语模式: {bilingual_text}\n"
            f"  历史消息: {history_count} 条\n"
            f"  难度: {self.difficulty}\n"
            f"  纠错: {self.correction_level}"
        )

    # ---- /lang reset ----
    @lang.command("reset")
    async def lang_reset(self, event: AstrMessageEvent):
        """重置对话历史"""
        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("当前没有进行中的口语练习。")
            return
        self.session_mgr.reset_history(user_id)
        yield event.plain_result("对话历史已重置，可以继续练习。")

    # ---- /lang bilingual ----
    @lang.command("bilingual")
    async def lang_bilingual(self, event: AstrMessageEvent):
        """切换双语回复模式（AI 同时用目标语种和中文回复）"""
        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)
        if not session.active:
            yield event.plain_result("请先使用 /lang start 开始练习。")
            return
        new_state = self.session_mgr.toggle_bilingual(user_id)
        state_text = "开启" if new_state else "关闭"
        yield event.plain_result(f"双语回复模式已{state_text}。")

    # ---- /lang help ----
    @lang.command("help")
    async def lang_help(self, event: AstrMessageEvent):
        """查看口语练习帮助"""
        help_text = (
            "外语口语助手 使用指南\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "/lang start [语种] [场景] - 开始练习\n"
            "/lang stop - 结束练习\n"
            "/lang lang <语种> - 切换语种\n"
            "/lang scene <场景> - 切换场景\n"
            "/lang switch <语种> <场景> - 同时切换\n"
            "/lang bilingual - 切换双语回复模式\n"
            "/lang list - 查看可用语种和场景\n"
            "/lang status - 查看当前状态\n"
            "/lang reset - 重置对话历史\n"
            "/lang help - 查看本帮助\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "语种支持: english/英语, japanese/日语\n"
            "场景可使用内置名称或自由描述，如:\n"
            "  /lang start 英语 在咖啡馆和朋友聊天\n"
            "开始练习后，直接发送消息即可对话。\n"
            "支持用中文或目标语种输入。\n"
            "用中文输入时，AI 会先翻译再回复。"
        )
        yield event.plain_result(help_text)

    # ==================== 消息接管 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """拦截活跃会话用户的所有消息，转发给 LLM 处理"""
        user_id = event.get_sender_id()
        session = self.session_mgr.get_session(user_id)

        if not session.active:
            return  # 不拦截，交给后续处理器

        # 跳过以 / 开头的指令消息
        msg = event.message_str.strip()
        if msg.startswith("/"):
            return

        # 阻断事件传播（不让 AstrBot 默认 LLM 处理）
        event.stop_event()

        try:
            # 构建 system prompt
            custom_prompt = None
            if session.scene in self._custom_scene_map:
                custom_prompt = self._custom_scene_map[session.scene]["prompt"]

            system_prompt = build_system_prompt(
                language=session.language,
                scene=session.scene,
                difficulty=self.difficulty,
                correction_level=self.correction_level,
                custom_prompt=custom_prompt,
                bilingual=session.bilingual,
            )

            # 构建对话上下文
            history = self.session_mgr.get_history(user_id)
            contexts = list(history)

            # 获取 Provider 并调用 LLM
            provider = self.context.get_using_provider(
                umo=event.unified_msg_origin
            )
            if provider is None:
                yield event.plain_result("未找到可用的 LLM Provider，请先在 AstrBot 中配置。")
                return

            resp = await provider.text_chat(
                prompt=msg,
                system_prompt=system_prompt,
                contexts=contexts,
            )

            reply_text = resp.completion_text

            # 保存对话历史
            self.session_mgr.add_message(user_id, "user", msg)
            self.session_mgr.add_message(user_id, "assistant", reply_text)

            yield event.plain_result(reply_text)

        except Exception as e:
            logger.error(f"外语口语助手 LLM 调用失败: {e}", exc_info=True)
            yield event.plain_result(f"对话出错了: {e!s}")

    # ==================== 辅助方法 ====================

    def _get_available_scenes(self) -> list[str]:
        """获取所有可用场景名（内置 + 自定义）"""
        scenes = list(SCENE_DISPLAY_NAMES.keys())
        scenes.extend(self._custom_scene_map.keys())
        return scenes

    def _get_scene_display_name(self, scene: str) -> str:
        """获取场景显示名称"""
        if scene in SCENE_DISPLAY_NAMES:
            return SCENE_DISPLAY_NAMES[scene]
        if scene in self._custom_scene_map:
            return self._custom_scene_map[scene]["display_name"]
        return scene

    async def terminate(self):
        logger.info("外语口语助手插件已卸载")
