# Auto Task Runner — 用户反馈优化 TODO 指南

> 基于用户反馈整理的改进清单，按优先级和独立性排序，便于逐项安排实施。

---

## 📋 Issue #1：Recent 完成列表增加完成时间

**现状：**
- `display/tracker.py` 的 `_render()` 在 Recent 区域只显示 `✅ M10 任务名 4m 18s`
- `record_result()` 只记录了 `task_no`, `task_name`, `status`, `elapsed`, `success`
- 用户无法知道上一个任务是什么时候完成的，时间间隔感知缺失

**改动范围：**
- [task_runner/display/tracker.py](task_runner/display/tracker.py)

**方案：**
1. 在 `record_result()` 中增加 `finished_at` 字段（`datetime.now().strftime("%H:%M:%S")`）
2. 在 `_render()` 的 Recent 区域渲染时追加完成时间戳

**改动前：**
```
✅ M10 会计要素（AccountElement）建模补齐  4m 18s
```

**改动后：**
```
✅ M10 会计要素（AccountElement）建模补齐  4m 18s  [12:34:56]
```

**难度：** ⭐ 简单
**预计工时：** 10 分钟
**依赖：** 无

---

## 📋 Issue #2：Running 状态的动画、开始时间、Elapsed 计时修复

### 问题分析

**2a — Spinner 动画不动：**
- `_render()` 中 spinner 基于 `tick = int(elapsed * 2)` 计算帧索引
- `elapsed = time.time() - self._current_start` 在每次 render 时实时计算
- Rich `Live` 设置了 `refresh_per_second=2`，理论上每 0.5s 刷新一次
- **但 Rich `Live` 的 auto-refresh 是基于上次 `update()` 后的 renderable 重新 render，如果 renderable 是 Panel 对象而非 callable，它不会重新调用 `_render()`**
- 根本原因：`Live` 的 auto-refresh 会重新渲染已有的 renderable，但 Panel 是静态对象。需要将 `_render` 作为 `get_renderable` 回调，或者用一个定时线程来调用 `_refresh()`

**可能修复方式（推荐）：**
- 方案 A：将 `Live` 的 renderable 改为一个实现 `__rich__()` 的对象，这样 auto-refresh 会每次调用 `__rich__()` 重新生成 Panel
- 方案 B：启动一个后台线程定时调用 `self._refresh()`（每 0.5s）

**推荐方案 A**，更简洁，不引入额外线程：
```python
class _TrackerRenderable:
    def __init__(self, tracker):
        self._tracker = tracker
    def __rich_console__(self, console, options):
        yield self._tracker._render()
```

然后 `Live(renderable=_TrackerRenderable(self), ...)` 即可让 auto-refresh 每次重新调用 `_render()`。

**2b — 显示开始时间：**
- 在 Running 行增加任务开始时间的显示
- `set_current_task()` 已经记录了 `_current_start = time.time()`，需要同时记录人类可读 `_current_start_str`

**改动后效果：**
```
⠋ Running │ M18 — 物料（Material）建模补齐  (started 14:30:05)
  Elapsed │ 3m 25s
```

**2c — Elapsed 不计时：**
- 这是 2a 的连带问题，spinner 不动说明 panel 没有重新渲染，elapsed 自然也不更新
- 修复 2a 后 2c 自动解决

**改动范围：**
- [task_runner/display/tracker.py](task_runner/display/tracker.py)

**难度：** ⭐⭐ 中等
**预计工时：** 30 分钟
**依赖：** 无

---

## 📋 Issue #3：默认工具改为 kimi

**现状：**
- `ProjectConfig` 的 `default_tool = "copilot"`，`default_model = "claude-opus-4.6"`
- `from_dict()` 反序列化时 fallback 也是 `copilot`

**改动范围：**
- [task_runner/project.py](task_runner/project.py) — `ProjectConfig` dataclass 默认值 + `from_dict()` fallback
- 建议同时检查 `commands/project_cmd.py` 创建项目时的逻辑是否硬编码了值

**方案：**
1. `default_tool` 改为 `"kimi"`
2. `default_model` 改为 `""` 或 `None`（kimi 不支持 model 选择）
3. `from_dict()` 中 fallback 同步改为 `"kimi"`

**注意事项：**
- 已有项目的 `__init__.json` 不受影响（已持久化）
- 仅影响新建项目和缺省字段的项目

**难度：** ⭐ 简单
**预计工时：** 10 分钟
**依赖：** 无

---

## 📋 Issue #4：单任务超时 40 分钟自动标记失败

**现状：**
- 没有任何上限超时机制
- 只有下限检查（< 10 秒标记失败）
- 如果 AI CLI 卡住，整个 pipeline 会永远阻塞

**改动范围：**
- [task_runner/executor.py](task_runner/executor.py) — 任务执行核心 `execute_task()` / PTY 读取循环

**方案：**
1. 新增配置常量 `MAX_EXECUTION_SECONDS = 2400`（40 分钟）
2. 支持通过 `--timeout` CLI 参数覆盖（或在 `__init__.json` 项目级配置）
3. 在 PTY 读取循环中检查已用时间，超时时：
   - 向子进程发送 `SIGTERM`
   - 等待 5 秒，若未退出发送 `SIGKILL`
   - 标记任务为 `failed`，`failure_reason = "timeout"`
   - 记录日志
   - 继续执行下一个任务
4. 在 Pipe fallback 模式中也加入相同超时逻辑

**实现要点：**
- PTY 模式：在 `select.select()` 循环中加时间判断
- PIPE 模式：使用 `subprocess.Popen.wait(timeout=...)` + 循环检查
- 或统一用监控线程在超时时 kill 子进程

**难度：** ⭐⭐⭐ 中等偏高
**预计工时：** 45-60 分钟
**依赖：** 无（但建议在 Issue #5 之前完成，提升稳定性）

---

## 📋 Issue #5：提升运行稳定性

这是一个综合性优化，包含多个子项：

### 5a — argparse 隐式导入修复
- `parse_delay_range()` 引用了 `argparse.ArgumentTypeError`，但 `argparse` 未在文件顶部导入
- 当前只是因为该函数从 argparse context 被调用才没出错
- **修复：** 在 `executor.py` 顶部增加 `import argparse`

### 5b — 子进程清理增强
- 当前 SIGTERM 后有 5s 等待 + SIGKILL，但在某些边缘情况下（如 PTY EOF 但进程未退出），清理逻辑分散
- **建议：** 在 `execute_task()` 的 finally 块中增加统一的子进程清理确认

### 5c — JSON 原子写入审计
- 当前使用 tmp + rename 模式（好！），确认所有写入路径都遵循此模式
- 检查是否有遗漏的直接 `open(f, 'w')` 写法

### 5d — 信号处理改进
- `_ctrl_c_count` 无锁递增，虽然 Python GIL 保证了原子性，但在信号处理器中建议使用更安全的模式
- 考虑用 `signal.pthread_sigmask` 或更安全的方式

### 5e — PTY/PIPE 降级日志
- 当 PTY 不可用降级到 PIPE 时，应有明确日志告知用户

**改动范围：**
- [task_runner/executor.py](task_runner/executor.py)
- 可能涉及 [task_runner/task_set.py](task_runner/task_set.py)、[task_runner/project.py](task_runner/project.py)

**难度：** ⭐⭐ 各子项简单，但需逐一排查
**预计工时：** 60 分钟（全部子项）
**依赖：** 无

---

## 📋 Issue #6：企业微信机器人通知集成

这是最大的功能新增，建议拆分为以下子任务：

### 6a — Webhook 通知基础架构
**新增文件：** `task_runner/notify.py`

**核心设计：**
```python
# 抽象基类，面向未来扩展（钉钉、飞书等）
class Notifier(ABC):
    @abstractmethod
    def send(self, message: dict) -> bool: ...

class WeComNotifier(Notifier):
    """企业微信群机器人通知"""
    def __init__(self, webhook_url: str): ...
    def send(self, message: dict) -> bool: ...
```

**环境变量配置：**
```bash
# 企业微信 Webhook
export TASK_RUNNER_WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# 未来扩展
# export TASK_RUNNER_DINGTALK_WEBHOOK="..."
# export TASK_RUNNER_FEISHU_WEBHOOK="..."

# 总开关
export TASK_RUNNER_NOTIFY_ENABLED="true"
```

也支持项目级 `__init__.json` 配置：
```json
{
  "notify": {
    "wecom_webhook": "https://...",
    "enabled": true
  }
}
```

优先级：环境变量 > 项目配置 > 关闭

### 6b — 消息模板设计

**任务完成通知（单任务级 — 可选，默认不发）：**
```
✅ 任务完成：M10 会计要素（AccountElement）建模补齐
项目：MASTER_DATA / master-data-v2
耗时：4m 18s
状态：成功
```

**批次/全部完成通知（必发）：**
```markdown
📊 任务批次执行完成

项目：MASTER_DATA
任务集：master-data-v2
执行时间：14:30:05 ~ 16:45:30（2h 15m）

📈 执行结果：
  ✅ 成功：12
  ❌ 失败：2
  ⏭️ 跳过：1

❌ 失败任务：
  - M18 物料（Material）建模补齐 — timeout (40m)
  - M22 客户（Customer）建模补齐 — exit code 1

下一步：python run.py run MASTER_DATA master-data-v2 --retry-failed
```

**中断通知：**
```
⚡ 任务执行中断

项目：MASTER_DATA / master-data-v2
中断时间：16:45:30
当前任务：M18 物料（Material）建模补齐
已完成：12/15
恢复命令：python run.py run MASTER_DATA master-data-v2
```

**错误通知：**
```
❌ 任务执行错误

项目：MASTER_DATA / master-data-v2
任务：M18 物料（Material）建模补齐
错误原因：超时 (40m) / 异常退出 / ...
耗时：40m 00s
```

### 6c — 企业微信 API 对接

根据文档 https://developer.work.weixin.qq.com/document/path/99110 ：

```python
import urllib.request
import json

def send_wecom_message(webhook_url: str, content: str, msg_type: str = "markdown") -> bool:
    """发送企业微信机器人消息"""
    payload = {
        "msgtype": msg_type,
        "markdown": {"content": content}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("errcode") == 0
    except Exception:
        return False  # 通知失败不应阻断任务执行
```

**关键原则：**
- 使用标准库 `urllib.request`，**不增加任何外部依赖**
- 通知失败不影响任务执行（catch all exceptions）
- 超时设为 10s，防止网络问题阻塞
- 通知发送使用独立线程，不阻塞主流程

### 6d — 接入执行引擎

**触发时机：**

| 事件 | 通知内容 | 默认开启 |
|------|---------|---------|
| 全部/批次完成 | 汇总统计 | ✅ 是 |
| 任务失败 | 失败详情 | ✅ 是 |
| 执行中断 (Ctrl+C) | 中断进度 | ✅ 是 |
| 单任务成功 | 任务完成信息 | ❌ 否（可通过 `--notify-each` 开启）|

**改动点：**
- `executor.py` — 在 `_run_v3()` 中注入 notifier
- `commands/run_cmd.py` — 新增 `--notify` / `--no-notify` / `--notify-each` CLI 参数
- `project.py` — ProjectConfig 新增 `notify` 配置段

### 6e — CLI 参数

```bash
# 使用环境变量中配置的 webhook（默认行为）
python run.py run MY_PROJECT tasks

# 显式关闭通知
python run.py run MY_PROJECT tasks --no-notify

# 每个任务完成都通知
python run.py run MY_PROJECT tasks --notify-each

# 命令行指定 webhook（覆盖环境变量）
python run.py run MY_PROJECT tasks --wecom-webhook "https://..."
```

**改动范围：**
- 新增 [task_runner/notify.py](task_runner/notify.py)
- 修改 [task_runner/executor.py](task_runner/executor.py)
- 修改 [task_runner/commands/run_cmd.py](task_runner/commands/run_cmd.py)
- 修改 [task_runner/project.py](task_runner/project.py)

**难度：** ⭐⭐⭐⭐ 较复杂（但可拆分实施）
**预计工时：** 2-3 小时（全部子任务）
**依赖：** 建议在 Issue #4 完成后再做（这样 timeout 错误也能推送通知）

---

## 🗓️ 建议实施顺序

```
优先级排序（由易到难、由核心到外围）：

第 1 轮 — 核心体验修复（30 min）
  ├── Issue #1  显示完成时间              [10 min] ⭐
  ├── Issue #2  修复 spinner/elapsed/开始时间  [20 min] ⭐⭐
  └── Issue #3  默认工具改 kimi            [10 min] ⭐

第 2 轮 — 稳定性增强（1.5 h）
  ├── Issue #4  40 分钟超时自动失败         [45 min] ⭐⭐⭐
  └── Issue #5  稳定性子项                 [45 min] ⭐⭐

第 3 轮 — 通知能力（2-3 h）
  ├── Issue #6a 通知基础架构               [30 min]
  ├── Issue #6b 消息模板                  [30 min]
  ├── Issue #6c 企业微信 API              [30 min]
  ├── Issue #6d 接入执行引擎              [45 min]
  └── Issue #6e CLI 参数                 [15 min]
```

---

## 📁 受影响文件一览

| 文件 | Issue | 改动类型 |
|------|-------|---------|
| `task_runner/display/tracker.py` | #1, #2 | 修改 |
| `task_runner/project.py` | #3, #6d | 修改 |
| `task_runner/executor.py` | #4, #5, #6d | 修改 |
| `task_runner/commands/run_cmd.py` | #4(?), #6e | 修改 |
| `task_runner/notify.py` | #6 | **新增** |
| `task_runner/config.py` | #4(常量) | 修改 |
| `README.md` | #6 | 更新文档 |
