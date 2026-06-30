# Main Memory

## About the User

- 服务器管理员，负责管理同网络环境下的多台服务器
- 使用 Ductor 多 agent 系统，本 agent 为 `serveradmin` 子 agent
- 通过 Telegram 与 agent 交互

## Managed Servers (2026-06-30)

- **Server A**: 独立计算服务器 (1 台) — agent 直接 SSH
- **Server B**: 集群登录节点 (1 台)，背后管理 5 台计算节点 — agent 仅能通过登录节点跳转访问计算节点
- SSH 客户端由 main agent 负责安装
- Agent 使用独立 SSH key pair（非共享用户 key），便于审计
- 所有服务器在同一网络环境下

## Task Scope & Autonomy (2026-06-30)

- **职责范围**: 
  - 监控巡检（磁盘、内存、服务状态等）
  - 用户管理（创建/修改/删除用户、权限调整）
  - 故障排查（日志分析、问题诊断）
- **自主权级别**: B — 只读自主 + 写入需确认
  - 查询/监控类命令可直接执行
  - 所有修改类操作必须经过严格审批
- **审批通知流程**: 暂定通过 main agent 中转通知用户

## Decisions and Preferences

- 2026-06-30: 修改操作审批采用严格模式，不做自主判断
- 2026-06-30: 审批通知路径暂定为 main → 用户（待最终确认）
- 2026-06-30: 监控告警流程：守护进程检测异常 + 初步分析（提取关键指标、抓相关日志片段）→ ask_agent_async 推送带初诊信息的告警给 serveradmin agent → agent 基于初诊信息深入分析、给出解决方案 → 只读直接执行，修改需 TOTP 审批。
- 2026-06-30: 任何周期性任务均不使用 cron，统一用守护进程或 systemd timer 替代。
- 2026-06-30: 项目已实现并部署到 GitHub (icamelot/server-admin-agent)，13 commits，98 测试通过。待重组为 skill library。
- 2026-06-30: 审批机制采用 TOTP 验证，TOTP secret 不由 agent 保存、不进入 agent 记忆。secret 由用户（或 main agent）持有，在目标服务器端做校验。agent 仅透传 TOTP 码，无法自主生成审批凭证。

--- SHARED KNOWLEDGE START ---
# Shared Knowledge — All Agents

Knowledge written here is automatically synced into every
agent's MAINMEMORY.md by the Supervisor.

Sub-agent 通知用户: 调用 enqueue_notification.py 写入共享队列, broker 守护进程每10秒推送到 Telegram。文件在 /ductor/workspace/tools/agent_tools/enqueue_notification.py。
--- SHARED KNOWLEDGE END ---
