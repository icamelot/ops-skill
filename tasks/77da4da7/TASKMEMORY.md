# Task: ops-skill-finalize

Created: 2026-07-01 04:32:49
Provider: /

## Task Description

完成三件事：

1. **修复 M1-M5**（工作目录 /ductor/agents/serveradmin/workspace）：
   - M1: agent_shell_filter.py 的 validate_totp 把 valid_window=1 改为 valid_window=0（TOTP 窗口从 90s 收紧到 60s，符合 spec）
   - M2: command_executor.py 的 _ssh_execute 中，根据 exit_code 和 stderr 内容动态设置 approved 字段。如果 stderr 包含 REJECTED 或 exit_code == -1 且非 timeout/FileNotFound，则 approved=False
   - M3: 为 monitor_daemon.py 的 _check_disk/_check_memory/_check_cpu/_check_service 添加测试。用 unittest.mock patch _ssh 方法返回模拟数据
   - M4: 创建 pytest.ini，配置 te

## Progress

_Update this section as you work._
