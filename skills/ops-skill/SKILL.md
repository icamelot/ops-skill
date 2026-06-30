# ops-skill

Secure remote server management — SSH command execution with TOTP-guarded
approval, monitoring daemon with pre-analysis, and defense-in-depth security
pipeline.

## Usage

Copy this skill into any Ductor agent's workspace under `skills/ops-skill/`.
Ensure `skills/ops-skill/` is on the Python path (add to `PYTHONPATH` or
the agent's startup script).

## Components

### Command Executor
Unified SSH command execution through a 5-layer security pipeline:
1. Command parser — splits chains, blocks injection
2. Whitelist router — read-only vs modifying classification
3. TOTP validation — format check client-side, cryptographic validation server-side
4. Rate limiter — max N modifying commands per hour (with optional disk persistence)
5. Audit log — append-only JSONL on both agent and server sides

### Agent Shell Filter
Server-side filter deployed to `/usr/local/bin/agent-shell-filter` on each
target server. Enforces TOTP validation against the local secret, performs
secondary whitelist checks, and blocks unconditionally dangerous commands
(rm -rf /, mkfs, shutdown, fork bombs, dd to block device).

### Monitor Daemon
Persistent health check daemon (`while True: sleep(N)` — no cron):
- Disk, memory, CPU, service health checks against configurable thresholds
- Pre-analysis on threshold breach (top consumers, journal logs)
- Alert deduplication (no repeat alerts for same condition)
- Bastion/jump host support for multi-tier infrastructure
- Alerts dispatched to agent via `ask_agent_async.py`

## Dependencies

```
pip3 install pyotp pyyaml
```

## Server Setup

1. Generate SSH key pair for the agent:
   ```bash
   ssh-keygen -t ed25519 -f .ssh/agent_key -C "agent@ops-skill"
   ```

2. Deploy `agent-shell-filter` to each target server:
   ```bash
   scp tools/executor/agent_shell_filter.py root@server:/usr/local/bin/
   chmod 755 /usr/local/bin/agent_shell_filter.py
   ```

3. Deploy TOTP secret to each server:
   ```bash
   echo "YOUR_BASE32_SECRET" > /etc/agent/totp_secret
   chmod 600 /etc/agent/totp_secret
   ```

4. Configure SSH forced-command in `~/.ssh/authorized_keys`:
   ```
   command="/usr/local/bin/agent_shell_filter.py",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 AAA...
   ```

5. Edit `config/thresholds.yaml` with server hostnames and thresholds.

6. Start the monitor daemon:
   ```bash
   python3 tools/monitor/monitor_daemon.py --config config/thresholds.yaml --ssh-key .ssh/agent_key &
   ```

## Structure

```
skills/ops-skill/
  SKILL.md
  __init__.py
  tools/
    __init__.py
    executor/
      __init__.py
      command_parser.py
      whitelist.py
      rate_limiter.py
      audit.py
      command_executor.py
      agent_shell_filter.py
    monitor/
      __init__.py
      monitor_daemon.py
      threshold_config.py
  config/
    thresholds.yaml
```
