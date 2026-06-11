# 提醒客户端 - AI 开发规则

## 版本管理

### 何时更新版本号

仅在以下情况下才需要更新版本号和变更日志：

- **代码逻辑或功能发生变更**（新增功能、修复 bug、界面改动、服务逻辑修改等）

纯文档修改（如 CLAUDE.md、AI-PRD.md、README 等）**不需要**更新版本号。

### 需要同步更新的四处位置

代码功能变更并推送到远程仓库前，必须同步更新以下四处，缺一不可：

1. **`pyproject.toml`** — `version` 字段
2. **`src/reminder_client/__init__.py`** — `__version__` 字段
3. **`.document/AI-PRD.md`** — "一、版本信息"表格，在最顶部新增一行，填写本次变更内容
4. **`src/reminder_client/ui/about_dialog.py`** — `_CHANGELOG` 字符串，在最顶部新增一段功能变更内容，无关内容不写入，格式与已有条目保持一致

### 版本号递增规则

- 小功能新增或 bug 修复 → 递增第三位（如 0.1.13 → 0.1.14）
- 较大功能或模块级重构 → 递增第二位（如 0.1.x → 0.2.0）

### GitHub Release

仅在代码功能变更时才创建新的 GitHub Release，上传最新打包的 `dist/ReminderClient.zip`。
