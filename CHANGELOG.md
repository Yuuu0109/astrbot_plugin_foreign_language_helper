# Changelog

## v1.0.2 (2026-05-20)

### 修复
- 对话持久化路径改为 plugin_data 插件专属目录

## v1.0.1 (2026-05-20)

### 修复
- 修复模块导入方式：将绝对导入改为相对导入，解决 AstrBot 加载插件时 `No module named 'core'` 的问题

## v1.0.0 (2026-05-20)

### 新增
- 外语口语助手插件初始版本
- 支持英语和日语两种语种的口语练习
- 6种内置对话场景：日常对话、餐厅点餐、机场出行、购物、面试、商务会议
- 支持自定义场景（通过 WebUI 配置 JSON）
- 中文输入自动翻译为目标语种后再回复
- /lang 命令组：start、stop、lang、scene、switch、list、status、reset、help
- 可配置难度等级（beginner/intermediate/advanced）
- 可配置纠错等级（off/light/strict）
- 对话历史持久化存储
- 可配置最大对话历史轮数
