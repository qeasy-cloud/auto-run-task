# Auto Task Runner — 用户操作指南

> 详细的操作指引、命令示例与典型工作流。项目概览请参阅 [README](../README.md)。

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

## 命令速查与示例

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
python run.py run FIX_CODE code-quality-fix --no-proxy  # 强制关闭代理

# 自定义模板
python run.py run FIX_CODE code-quality-fix --template templates/custom.md

# 指定工作目录（覆盖项目配置）
python run.py run FIX_CODE code-quality-fix --work-dir /other/repo

# Git 安全模式（执行前自动创建 git tag 作为回退点）
python run.py run FIX_CODE code-quality-fix --git-safety

# 任务间延时控制（防止被检测为机器人）
python run.py run FIX_CODE code-quality-fix --delay 60-120   # 随机 60~120s（默认）
python run.py run FIX_CODE code-quality-fix --delay 30       # 固定 30s
python run.py run FIX_CODE code-quality-fix --delay 0       # 不延时

# 企业微信通知（需配置 TASK_RUNNER_WECOM_WEBHOOK 环境变量）
python run.py run FIX_CODE code-quality-fix                  # 默认启用
python run.py run FIX_CODE code-quality-fix --no-notify      # 关闭通知
python run.py run FIX_CODE code-quality-fix --notify-each    # 每个任务完成都通知
python run.py run FIX_CODE code-quality-fix --wecom-webhook "https://..."  # 命令行指定 webhook

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

## 数据结构详解

### `__init__.json` — 项目配置

```json
{
  "project": "FIX_CODE",
  "description": "A project to fix code issues",
  "workspace": "/home/user/workspace/my-repo",
  "status": "planned",
  "created_at": "2024-06-01_10-00-00",
  "default_tool": "kimi",
  "default_model": "",
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
4. **全局默认** — `kimi` / 空（kimi 不支持 model 选择）

---

## Prompt 模板格式

模板使用两种占位符：

| 占位符    | 替换为                       | 示例                       |
| --------- | ---------------------------- | -------------------------- |
| `{{key}}` | `task[key]` 的值             | `{{task_name}}` → 任务名称 |
| `#item`   | 整个 task 对象的 JSON 字符串 | 完整任务上下文             |

如果值是 dict/list 类型，会自动序列化为 JSON 字符串。

---

## 代理控制逻辑

| 工具    | `--proxy` | `--no-proxy` | 默认行为     |
| ------- | --------- | ------------ | ------------ |
| kimi    | 启用代理  | 关闭代理     | **关闭代理** |
| agent   | 启用代理  | 关闭代理     | **启用代理** |
| copilot | 启用代理  | 关闭代理     | **启用代理** |
| claude  | 启用代理  | 关闭代理     | **启用代理** |

---

## 企业微信通知

配置环境变量 `TASK_RUNNER_WECOM_WEBHOOK` 后，任务执行会在以下时机自动推送通知：

| 事件 | 默认 |
|------|------|
| 批次/全部完成 | ✅ |
| 任务失败 | ✅ |
| Ctrl+C 中断 | ✅ |
| 单任务成功 | ❌（需 `--notify-each`） |

```bash
export TASK_RUNNER_WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
python run.py run MY_PROJECT tasks
```

---

## 执行安全机制

| 机制 | 说明 |
| --- | --- |
| **最短执行时间** | AI CLI 执行不足 10 秒自动标记为失败（防止空跑误标成功） |
| **单任务超时** | 默认 40 分钟，超时自动终止并标记失败，`--timeout` 可调整 |
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

---

## 调试

```bash
DEBUG=1 python run.py run MY_PROJECT my-tasks
```

---

## Legacy 兼容（已弃用）

旧版 `--plan` 模式仍可使用，但会显示弃用警告，将在 v4.0 移除：

```bash
python run.py --plan plan.json --project my-fix --template prompt.md
```
