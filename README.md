# 外语口语助手 (astrbot_plugin_foreign_language_helper)

一个基于 AstrBot 的外语口语练习插件，通过大模型进行英语/日语口语对话练习，支持多场景切换。

## 功能特性

- 支持 **英语** 和 **日语** 两种语言的口语练习
- 6 种内置对话场景：日常对话、餐厅点餐、机场出行、购物、面试、商务会议
- 支持自定义场景（在 WebUI 配置中添加）
- 支持用 **中文** 或 **目标语种** 输入
- 中文输入时，AI 会先翻译成目标语种再回复
- 支持 **双语回复模式**（AI 同时用目标语种和中文回复）
- 支持 **语音回复模式**（AI 同时发送语音和文本，仅朗读外语正文，需配置 TTS Provider）
- 可配置难度等级、纠错等级、历史轮数等参数
- 对话历史持久化存储

## 使用方法

### 指令列表

| 指令 | 说明 |
|------|------|
| `/lang start [语种] [场景]` | 开始口语练习 |
| `/lang stop` | 结束练习 |
| `/lang lang <语种>` | 切换目标语种 |
| `/lang scene <场景>` | 切换对话场景 |
| `/lang switch <语种> <场景>` | 同时切换语种和场景 |
| `/lang bilingual` | 切换双语回复模式 |
| `/lang voice` | 切换语音回复模式 |
| `/lang list` | 查看可用语种和场景 |
| `/lang status` | 查看当前练习状态 |
| `/lang reset` | 重置对话历史 |
| `/lang help` | 查看帮助 |

### 快速开始

1. 发送 `/lang start` 使用默认配置开始练习
2. 或指定语种和场景：`/lang start english restaurant`
3. 直接发送消息进行对话（支持中文或目标语种）
4. 发送 `/lang stop` 结束练习

## 配置项

在 AstrBot WebUI 的插件配置中可以修改以下参数：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `default_language` | string | english | 默认目标语种 |
| `default_scene` | string | daily | 默认对话场景 |
| `max_history_rounds` | int | 10 | 最大对话历史轮数 |
| `correction_level` | string | light | 纠错等级 (off/light/strict) |
| `difficulty` | string | intermediate | 难度等级 (beginner/intermediate/advanced) |
| `custom_scenes` | text | [] | 自定义场景（JSON 数组字符串） |
| `enable_voice` | bool | false | 是否默认启用语音回复（需配置 TTS Provider） |

## 依赖

- AstrBot >= v4.5.0
- 需要在 AstrBot 中配置至少一个 LLM Provider
