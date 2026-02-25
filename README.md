# Auto Task Runner v3.0

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Powered by QeasyCloud](https://img.shields.io/badge/Powered%20by-轻易云-orange.svg)](https://www.qeasy.cloud)

> 项目化 AI Agent CLI 批量任务执行引擎 — 支持多工具、多模型、项目管理、任务集、运行历史

**Auto Task Runner** 是由 [广东轻亿云软件科技有限公司（QeasyCloud）](https://www.qeasy.cloud) 研发团队开源的 AI Agent 批量任务执行引擎。
将结构化的任务集（`.tasks.json`）+ Prompt 模板，批量交给 AI Agent CLI 自动执行。
适用于大规模代码迁移、批量修复、自动化重构等场景。

> 💡 **[轻易云数据集成平台](https://www.qeasy.cloud)** 是我们的核心产品 —— 一站式数据集成解决方案，
> 连接 200+ 应用系统，实现企业数据自动化流转。Auto Task Runner 正是我们在
> AI 辅助研发实践中沉淀出的工程工具。

## 特性

- 📁 **项目化架构** — 以项目为中心，支持多任务集、运行历史、模板管理
- 🔧 **多工具支持** — kimi / agent (Claude Code) / copilot / claude，一键切换
- 🤖 **多模型选择** — 项目级、任务集级、任务级可独立配置 tool/model
- 📋 **结构化任务集** — `.tasks.json` 定义任务，`{{key}}` + `#item` 模板渲染
- 🗂️ **运行时管理** — 每次运行自动创建运行目录、备份任务集、记录历史
- 🎯 **智能调度** — batch + priority 排序，依赖验证，支持过滤和重试
- ✅ **验证框架** — 项目结构、工作空间、任务集全面校验
- 🎨 **丰富终端** — Rich 面板、进度条、心跳动画、项目仪表板
- 🌐 **代理自动控制** — kimi 免代理，其他工具自动启用代理
- 🔄 **断点续跑** — 状态实时持久化，中断后从上次位置继续
- 🛡️ **健壮可靠** — PTY 色彩保留、原子写入、优雅信号处理、git 安全标签
- ⏱️ **防误标** — AI CLI 执行低于 10s 自动标记失败（防止空跑）
- 🕐 **防封号** — 任务间随机延时（默认 60-120s），降低被检测为机器人的风险

---

## 快速上手（5 分钟）

### 第 1 步：安装

```bash
git clone https://github.com/qeasy-cloud/auto-run-task.git
cd auto-run-task
pip install rich           # 唯一依赖
```

### 第 2 步：创建项目

```bash
python run.py project create MY_PROJECT \
  --workspace /path/to/your/repo \
  --description "我的批量修复项目"
```

这会在 `projects/MY_PROJECT/` 下生成项目骨架：

```
projects/MY_PROJECT/
├── __init__.json           # 项目配置
├── templates/
│   └── __init__.md         # 默认 Prompt 模板（可编辑）
└── runtime/                # 运行时输出（自动生成）
```

### 第 3 步：编写 Prompt 模板

编辑 `projects/MY_PROJECT/templates/__init__.md`：

```markdown
## Task: {{task_name}}

### Description
{{description}}

### Task Data
\`\`\`json
#item
\`\`\`

### Instructions
1. Read the task description and understand the requirement
2. Implement the changes following project conventions
3. Verify your changes
```

- `{{key}}` — 替换为任务字段值（如 `{{task_name}}`, `{{description}}`）
- `#item` — 替换为整个任务对象的 JSON

### 第 4 步：创建任务集

在项目目录下创建 `projects/MY_PROJECT/fix-bugs.tasks.json`：

```json
{
  "template": "templates/__init__.md",
  "tasks": [
    {
      "task_no": "F-1",
      "task_name": "修复用户登录验证",
      "batch": 1,
      "description": "用户登录时未校验密码强度",
      "priority": 10,
      "status": "not-started"
    },
    {
      "task_no": "F-2",
      "task_name": "修复订单金额计算",
      "batch": 1,
      "description": "订单金额小数精度丢失",
      "priority": 20,
      "status": "not-started"
    },
    {
      "task_no": "F-3",
      "task_name": "添加接口鉴权",
      "batch": 2,
      "description": "REST API 缺少 JWT 鉴权中间件",
      "priority": 10,
      "status": "not-started",
      "depends_on": "F-1"
    }
  ]
}
```

### 第 5 步：执行！

```bash
# 先预览（不真正执行）
python run.py dry-run MY_PROJECT fix-bugs

# 确认无误后执行
python run.py run MY_PROJECT fix-bugs
```

---

## 命令速查表

### 总览

| 命令 | 说明 |
| --- | --- |
| `project create` | 创建新项目 |
| `project list` | 列出所有项目 |
| `project info` | 查看项目详情 |
| `project validate` | 校验项目结构 |
| `project archive` | 归档项目 |
| `run` | 执行任务 |
| `dry-run` | 预览模式（只生成 prompt 不执行） |
| `reset` | 重置任务状态（用于重跑） |
| `list` | 列出任务集/任务 |
| `status` | 项目状态仪表板 |

### 项目管理

```bash
# 创建项目
python run.py project create FIX_CODE --workspace /path/to/repo --description "修复代码"

# 列出所有项目
python run.py project list

# 查看项目详情（任务集、运行历史等）
python run.py project info FIX_CODE

# 验证项目结构是否正确
python run.py project validate FIX_CODE

# 归档项目（标记为 archived）
python run.py project archive FIX_CODE
```

### 执行任务

```bash
# 基本执行（使用项目默认 tool/model）
python run.py run FIX_CODE code-quality-fix

# 指定工具和模型
python run.py run FIX_CODE code-quality-fix --tool agent --model opus-4.6
python run.py run FIX_CODE code-quality-fix --tool kimi
python run.py run FIX_CODE code-quality-fix --tool copilot --model claude-opus-4.6

# 只运行指定批次
python run.py run FIX_CODE code-quality-fix --batch 1

# 从指定任务开始（跳过前面的任务）
python run.py run FIX_CODE code-quality-fix --start F-3

# 只重跑失败的任务
python run.py run FIX_CODE code-quality-fix --retry-failed

# 代理控制
python run.py run FIX_CODE code-quality-fix --proxy      # 强制启用代理
python run.py run FIX_CODE code-quality-fix --no-proxy    # 强制关闭代理

# 自定义模板
python run.py run FIX_CODE code-quality-fix --template templates/custom.md

# 指定工作目录（覆盖项目配置）
python run.py run FIX_CODE code-quality-fix --work-dir /other/repo

# Git 安全模式（执行前自动创建 git tag 作为回退点）
python run.py run FIX_CODE code-quality-fix --git-safety

# 任务间延时控制（防止被检测为机器人）
python run.py run FIX_CODE code-quality-fix --delay 60-120   # 随机 60~120s（默认）
python run.py run FIX_CODE code-quality-fix --delay 30       # 固定 30s
python run.py run FIX_CODE code-quality-fix --delay 0        # 不延时

# 输出控制
python run.py run FIX_CODE code-quality-fix --verbose    # 详细模式
python run.py run FIX_CODE code-quality-fix --quiet      # 安静模式
python run.py run FIX_CODE code-quality-fix --no-color   # 无颜色（CI 环境）

# 心跳间隔
python run.py run FIX_CODE code-quality-fix --heartbeat 30   # 每 30s 打印一次状态
```

### 重置任务状态

当你需要重新执行任务时，先重置状态再运行：

```bash
# 重置所有失败的任务
python run.py reset FIX_CODE code-quality-fix --status failed

# 重置所有被中断的任务
python run.py reset FIX_CODE code-quality-fix --status interrupted

# 从 F-3 开始的所有任务重置
python run.py reset FIX_CODE code-quality-fix --from F-3

# 重置全部任务（完全重跑）
python run.py reset FIX_CODE code-quality-fix --all

# 只重置第 2 批中失败的任务
python run.py reset FIX_CODE code-quality-fix --status failed --batch 2

# 重置后执行
python run.py reset FIX_CODE code-quality-fix --status failed
python run.py run FIX_CODE code-quality-fix --retry-failed

# 或者重置后从某个任务开始执行
python run.py reset FIX_CODE code-quality-fix --from F-3
python run.py run FIX_CODE code-quality-fix --start F-3
```

### Dry-run 预览

```bash
# 生成 prompt 但不执行（检查渲染结果）
python run.py dry-run FIX_CODE code-quality-fix

# 预览指定批次
python run.py dry-run FIX_CODE code-quality-fix --batch 1
```

### 列出任务

```bash
# 列出项目内所有任务集
python run.py list FIX_CODE

# 列出特定任务集的任务
python run.py list FIX_CODE code-quality-fix

# 按状态过滤
python run.py list FIX_CODE code-quality-fix --status failed
python run.py list FIX_CODE code-quality-fix --status completed
python run.py list FIX_CODE code-quality-fix --status not-started
```

### 状态仪表板

```bash
# 全局仪表板（所有项目概览）
python run.py status

# 单项目详情
python run.py status FIX_CODE
```

---

## 典型工作流

### 场景 1：批量修复 → 检查 → 重跑失败

```bash
# 1. 创建项目
python run.py project create BUG_FIX --workspace /home/user/my-app

# 2. 编写任务集 + 模板（见上方说明）

# 3. 预览确认
python run.py dry-run BUG_FIX fix-bugs

# 4. 执行全部任务
python run.py run BUG_FIX fix-bugs

# 5. 查看结果
python run.py list BUG_FIX fix-bugs --status failed
python run.py status BUG_FIX

# 6. 重跑失败的任务
python run.py run BUG_FIX fix-bugs --retry-failed

# 7. 如果需要完全重跑某些任务
python run.py reset BUG_FIX fix-bugs --from F-5
python run.py run BUG_FIX fix-bugs --start F-5
```

### 场景 2：分批执行大量任务

```bash
# 先跑第 1 批（基础任务）
python run.py run MY_PROJECT migration --batch 1

# 手动检查结果后，再跑第 2 批
python run.py run MY_PROJECT migration --batch 2

# 最后跑第 3 批
python run.py run MY_PROJECT migration --batch 3
```

### 场景 3：不同任务用不同 AI 工具

在 `.tasks.json` 中为不同任务指定不同的 tool/model：

```json
{
  "tasks": [
    { "task_no": "T-1", "cli": { "tool": "kimi" }, "..." : "..." },
    { "task_no": "T-2", "cli": { "tool": "agent", "model": "opus-4.6" }, "..." : "..." },
    { "task_no": "T-3", "cli": { "tool": "copilot", "model": "claude-opus-4.6" }, "..." : "..." }
  ]
}
```

### 场景 4：中断后继续

```bash
# 执行过程中按 CTRL+C 优雅中断
# 已完成的任务状态已保存，再次运行会自动跳过已完成的任务
python run.py run MY_PROJECT my-tasks
# → 自动从上次中断的位置继续
```

---

## 支持的工具

| 工具      | 默认模型          | 需要代理 | 说明                    |
| --------- | ----------------- | -------- | ----------------------- |
| `kimi`    | —                 | ✗        | Kimi AI CLI（默认工具） |
| `agent`   | `opus-4.6`        | ✓        | Claude Code Agent CLI   |
| `copilot` | `claude-opus-4.6` | ✓        | GitHub Copilot CLI      |
| `claude`  | 固定              | ✓        | Claude CLI（单模型）    |

## 项目结构

```
auto-run-task/
├── run.py                          # 入口 (子命令分发)
├── task_runner/
│   ├── __init__.py                 # v3.0.0
│   ├── cli.py                      # 子命令架构 + Legacy 兼容
│   ├── config.py                   # 工具/模型配置
│   ├── display/                    # Rich 终端显示（模块化）
│   │   ├── __init__.py             # 统一导出
│   │   ├── core.py                 # Console 单例 & 常量
│   │   ├── banners.py              # 启动横幅
│   │   ├── tasks.py                # 任务列表 & 执行展示
│   │   ├── tracker.py              # Rich Live 实时面板
│   │   ├── summary.py              # 执行摘要 & 进度条
│   │   ├── projects.py             # 项目仪表板
│   │   └── messages.py             # 错误/警告/提示消息
│   ├── executor.py                 # PTY 任务执行引擎
│   ├── renderer.py                 # 模板渲染
│   ├── state.py                    # Legacy 状态管理
│   ├── project.py                  # 项目 CRUD + 验证
│   ├── task_set.py                 # 任务集加载/验证/保存
│   ├── runtime.py                  # 运行时目录管理
│   ├── scheduler.py                # 调度器（排序/过滤/依赖）
│   ├── validators.py               # 验证框架
│   └── commands/                   # 命令处理器
│       ├── project_cmd.py          # project 子命令
│       ├── run_cmd.py              # run 子命令
│       ├── dryrun_cmd.py           # dry-run 子命令
│       ├── reset_cmd.py            # reset 子命令
│       ├── list_cmd.py             # list 子命令
│       └── status_cmd.py           # status 子命令
├── projects/                       # 项目目录 (gitignored)
│   └── EXAMPLE/                    # 示例项目
└── example/                        # 旧版示例（供参考）
```

### 项目目录结构

```
projects/FIX_CODE/
├── __init__.json                   # 项目元数据（必须）
├── code-quality-fix.tasks.json     # 任务集文件（可多个）
├── feature-dev.tasks.json
├── templates/                      # 提示词模板目录
│   ├── __init__.md                 # 默认模板（必须）
│   └── custom-fix.md              # 自定义模板
└── runtime/                        # 运行时输出
    ├── runs/                       # 按运行记录存储
    │   └── 2024-06-01_10-00-00__code-quality-fix/
    │       ├── run.json            # 运行元数据
    │       ├── prompts/            # 渲染后的 prompt
    │       ├── logs/               # 执行日志（.log 原始 + .clean.log 净化版）
    │       └── summary.json        # 运行摘要
    ├── latest -> runs/...          # 最新运行的软链接
    └── backups/                    # 任务集备份
```

## 数据结构

### `__init__.json` — 项目配置

```json
{
  "project": "FIX_CODE",
  "description": "A project to fix code issues",
  "workspace": "/home/user/workspace/my-repo",
  "status": "planned",
  "created_at": "2024-06-01_10-00-00",
  "default_tool": "copilot",
  "default_model": "claude-opus-4.6",
  "tags": ["code-quality"],
  "run_record": [
    {
      "run_at": "2024-06-01_10-00-00",
      "stop_at": "2024-06-01_12-00-00",
      "cumulated_minutes": 120,
      "status": "completed",
      "task_set_name": "code-quality-fix",
      "tasks_attempted": 6,
      "tasks_succeeded": 5,
      "tasks_failed": 1
    }
  ]
}
```

### `.tasks.json` — 任务集

```json
{
  "template": "templates/__init__.md",
  "tasks": [
    {
      "task_no": "F-1",
      "task_name": "创建 Product 模型",
      "batch": 1,
      "description": "创建 Product 模型，包含 name, code 等字段",
      "priority": 10,
      "status": "not-started",
      "depends_on": null,
      "cli": { "tool": "copilot", "model": "claude-opus-4.6" }
    }
  ]
}
```

**任务字段说明：**

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `task_no` | ✓ | 任务编号（如 `F-1`, `RT-001`），全局唯一 |
| `task_name` | ✓ | 任务名称 |
| `batch` | | 批次号（默认 1），同批次内按 priority 排序 |
| `description` | | 任务描述，渲染到 prompt 模板 |
| `priority` | | 优先级（越小越先执行，默认 50） |
| `status` | | 状态：`not-started` / `in-progress` / `completed` / `failed` / `interrupted` |
| `prompt` | | 任务级模板覆盖（相对路径） |
| `cli.tool` | | 任务级工具覆盖 |
| `cli.model` | | 任务级模型覆盖 |
| `depends_on` | | 依赖的任务编号 |

### 默认值解析链

任务的 `tool` 和 `model` 按以下优先级解析：

1. **任务级** — `task.cli.tool` / `task.cli.model`
2. **命令行级** — `--tool` / `--model`
3. **项目级** — `__init__.json` 中的 `default_tool` / `default_model`
4. **全局默认** — `copilot` / `claude-opus-4.6`

## Prompt 模板格式

模板使用两种占位符：

| 占位符    | 替换为                       | 示例                       |
| --------- | ---------------------------- | -------------------------- |
| `{{key}}` | `task[key]` 的值             | `{{task_name}}` → 任务名称 |
| `#item`   | 整个 task 对象的 JSON 字符串 | 完整任务上下文             |

如果值是 dict/list 类型，会自动序列化为 JSON 字符串。

## 代理控制逻辑

| 工具    | `--proxy` | `--no-proxy` | 默认行为     |
| ------- | --------- | ------------ | ------------ |
| kimi    | 启用代理  | 关闭代理     | **关闭代理** |
| agent   | 启用代理  | 关闭代理     | **启用代理** |
| copilot | 启用代理  | 关闭代理     | **启用代理** |
| claude  | 启用代理  | 关闭代理     | **启用代理** |

## 执行安全机制

| 机制 | 说明 |
| --- | --- |
| **最短执行时间** | AI CLI 执行不足 10 秒自动标记为失败（防止空跑误标成功） |
| **任务间延时** | 默认随机等待 60-120 秒，降低触发反爬/封号风险，`--delay 0` 可关闭 |
| **PTY 色彩保留** | 使用伪终端执行，AI CLI 的彩色输出原样呈现 |
| **自动降级** | PTY 不可用时自动切换 PIPE 模式 |
| **日志全量捕获** | 终端实时输出的同时写入日志文件，同时生成去噪净化版 `.clean.log` |
| **心跳 & 标题** | 长时间运行时定期打印状态，终端标题显示任务进度 |
| **优雅中断** | 第一次 CTRL+C 优雅终止当前任务并保存状态，第二次强制退出 |
| **状态持久化** | 每个任务完成后立即更新 JSON，崩溃后可从断点续跑 |
| **原子写入** | JSON 保存使用 tmp + rename，防止写入中途断电损坏 |
| **自动备份** | 执行前自动备份 .tasks.json 文件 |
| **运行历史** | 每次运行自动记录到 __init__.json |
| **latest 软链接** | runtime/latest 始终指向最新运行目录 |
| **Git 安全** | --git-safety 执行前检查 git 状态并创建安全 tag |

## 环境要求

- Python 3.11+
- `rich` Python 包
- 对应的 AI CLI 工具已安装并在 PATH 中
- 需要代理的工具，确保系统已配置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量

## 调试

```bash
DEBUG=1 python run.py run MY_PROJECT my-tasks
```

## Legacy 兼容（已弃用）

旧版 `--plan` 模式仍可使用，但会显示弃用警告，将在 v4.0 移除：

```bash
python run.py --plan plan.json --project my-fix --template prompt.md
```

## 开源信息

### 许可证

本项目基于 [MIT License](LICENSE) 开源。您可以自由使用、修改和分发本软件。

### 作者

**广东轻亿云软件科技有限公司（QeasyCloud）** 研发团队

- 🏢 公司：广东轻亿云软件科技有限公司
- 🌐 官网：[https://www.qeasy.cloud](https://www.qeasy.cloud)
- 🚀 核心产品：[轻易云数据集成平台](https://www.qeasy.cloud) — 连接 200+ 应用，一站式企业数据集成
- 📦 GitHub：[https://github.com/qeasy-cloud](https://github.com/qeasy-cloud)

### 相关开源项目

| 项目 | 说明 |
| --- | --- |
| [auto-run-task](https://github.com/qeasy-cloud/auto-run-task) | AI Agent CLI 批量任务执行引擎（本项目） |

### 贡献

欢迎提交 Issue 和 Pull Request！请参阅项目的 GitHub 仓库参与贡献。

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://www.qeasy.cloud">轻易云 QeasyCloud</a> R&D Team</sub>
</p>
