# Auto Task Runner v3.0

> 项目化 AI Agent CLI 批量任务执行引擎 — 支持多工具、多模型、项目管理、任务集、运行历史

将结构化的任务集（`.tasks.json`）+ Prompt 模板，批量交给 AI Agent CLI 自动执行。
适用于大规模代码迁移、批量修复、自动化重构等场景。

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

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/auto-run-task.git
cd auto-run-task

# 2. 安装依赖
pip install rich
# 或
bash setup.sh

# 3. 创建项目
python run.py project create MY_PROJECT --workspace /path/to/repo --description "我的项目"

# 4. 在项目目录下创建任务集文件 (projects/MY_PROJECT/my-tasks.tasks.json)

# 5. 执行任务
python run.py run MY_PROJECT my-tasks
```

## CLI 用法

### 项目管理

```bash
# 创建项目
python run.py project create FIX_CODE --workspace /path/to/repo --description "修复代码"

# 列出所有项目
python run.py project list

# 查看项目详情
python run.py project info FIX_CODE

# 验证项目结构
python run.py project validate FIX_CODE

# 归档项目
python run.py project archive FIX_CODE
```

### 执行任务

```bash
# 基本执行
python run.py run FIX_CODE code-quality-fix

# 指定工具和模型
python run.py run FIX_CODE code-quality-fix --tool agent --model opus-4.6

# 只运行指定批次
python run.py run FIX_CODE code-quality-fix --batch 1

# 从指定任务开始
python run.py run FIX_CODE code-quality-fix --start F-3

# 重跑失败的任务
python run.py run FIX_CODE code-quality-fix --retry-failed

# Git 安全模式（执行前创建 tag）
python run.py run FIX_CODE code-quality-fix --git-safety
```

### 列出任务

```bash
# 列出项目内所有任务集
python run.py list FIX_CODE

# 列出特定任务集的任务
python run.py list FIX_CODE code-quality-fix

# 按状态过滤
python run.py list FIX_CODE code-quality-fix --status failed
```

### Dry-run

```bash
# 生成 prompt 但不执行
python run.py dry-run FIX_CODE code-quality-fix
```

### 状态仪表板

```bash
# 多项目仪表板
python run.py status

# 单项目详情
python run.py status FIX_CODE
```

### Legacy 兼容（已弃用）

```bash
# 旧版 --plan 模式仍可使用，但会显示弃用警告
python run.py --plan plan.json --project my-fix --template prompt.md
```

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
│   ├── display.py                  # Rich 终端显示
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
    │       ├── logs/               # 执行日志
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

## 运行特性

| 特性          | 说明                                                     |
| ------------- | -------------------------------------------------------- |
| PTY 色彩保留  | 使用伪终端执行，AI CLI 的彩色输出原样呈现                |
| 自动降级      | PTY 不可用时自动切换 PIPE 模式                           |
| 日志全量捕获  | 终端实时输出的同时写入日志文件                           |
| 心跳 & 标题   | 长时间运行时定期打印状态，终端标题显示任务进度           |
| 优雅中断      | 第一次 CTRL+C 优雅终止当前任务并保存状态，第二次强制退出 |
| 状态持久化    | 每个任务完成后立即更新 JSON，崩溃后可从断点续跑          |
| 原子写入      | JSON 保存使用 tmp + rename，防止写入中途断电损坏         |
| 自动备份      | 执行前自动备份 .tasks.json 文件                          |
| 运行历史      | 每次运行自动记录到 __init__.json                         |
| latest 软链接 | runtime/latest 始终指向最新运行目录                      |
| Git 安全      | --git-safety 执行前检查 git 状态并创建安全 tag           |

## 环境要求

- Python 3.11+
- `rich` Python 包
- 对应的 AI CLI 工具已安装并在 PATH 中
- 需要代理的工具，确保系统已配置 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量

## 调试

```bash
DEBUG=1 python run.py run MY_PROJECT my-tasks
```

## License

MIT
