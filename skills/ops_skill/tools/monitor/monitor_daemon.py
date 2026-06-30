#!/usr/bin/env python3
"""
Monitoring daemon — persistent health check loop with pre-analysis.

Runs as a long-lived process (no cron). Periodically SSHes to all configured
servers, runs health checks against thresholds, performs preliminary analysis
when thresholds are breached, and dispatches alerts to the serveradmin agent
via ask_agent_async.py.
"""

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone

from skills.ops_skill.tools.monitor.threshold_config import ThresholdConfig


# Path to workspace for inter-agent communication
WORKSPACE_ROOT = "/ductor/agents/serveradmin/workspace"
ASK_AGENT_ASYNC = os.path.join(WORKSPACE_ROOT, "tools", "agent_tools", "ask_agent_async.py")


class MonitorDaemon:
    """Persistent monitoring daemon with pre-analysis capabilities."""

    def __init__(
        self,
        config_path: str,
        ssh_key_path: str,
        ssh_user: str = "agent",
    ):
        self.config = ThresholdConfig(config_path)
        self.ssh_key_path = ssh_key_path
        self.ssh_user = ssh_user
        self._sustained_cpu: dict[str, int] = {}  # server -> consecutive checks over threshold
        self._last_alerts: dict[str, dict] = {}  # key -> {level, time} for dedup

    def run(self) -> None:
        """Main monitoring loop. Blocks forever."""
        print(f"[{self._now()}] Monitor daemon started. "
              f"Interval: {self.config.check_interval}s", file=sys.stderr)

        while True:
            try:
                self._check_all_servers()
            except Exception as e:
                print(f"[{self._now()}] Error in check cycle: {e}", file=sys.stderr)

            time.sleep(self.config.check_interval)

    def _check_all_servers(self) -> None:
        """Run health checks on all configured servers."""
        for server_id in self.config.get_servers():
            hostname = self.config.get_hostname(server_id)
            thresholds = self.config.get_thresholds(server_id)
            jump_host = thresholds.get("jump_host")

            alerts: list[dict] = []

            # Disk check
            disk_alert = self._check_disk(hostname, thresholds, jump_host=jump_host)
            if disk_alert and self._should_dispatch(server_id, disk_alert):
                alerts.append(disk_alert)

            # Memory check
            mem_alert = self._check_memory(hostname, thresholds, jump_host=jump_host)
            if mem_alert and self._should_dispatch(server_id, mem_alert):
                alerts.append(mem_alert)

            # CPU check
            cpu_alert = self._check_cpu(server_id, hostname, thresholds, jump_host=jump_host)
            if cpu_alert and self._should_dispatch(server_id, cpu_alert):
                alerts.append(cpu_alert)

            # Service checks
            for svc in self.config.services:
                svc_alert = self._check_service(hostname, svc, jump_host=jump_host)
                if svc_alert and self._should_dispatch(server_id, svc_alert):
                    alerts.append(svc_alert)

            if alerts:
                self._dispatch_alert(server_id, hostname, alerts)

    def _ssh(self, hostname: str, command: str,
             jump_host: str | None = None) -> tuple[int, str, str]:
        """Run a command via SSH and return (exit_code, stdout, stderr).

        If jump_host is provided, adds -J user@jump_host to the SSH command.
        """
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            "-i", self.ssh_key_path,
        ]
        if jump_host:
            ssh_cmd.append("-J")
            ssh_cmd.append(f"{self.ssh_user}@{jump_host}")
        ssh_cmd += [
            f"{self.ssh_user}@{hostname}",
            command,
        ]
        try:
            proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except subprocess.TimeoutExpired:
            return -1, "", "SSH timeout"
        except FileNotFoundError:
            return -1, "", "SSH client not available"
        except Exception as e:
            return -1, "", str(e)

    def _check_disk(self, hostname: str, thresholds: dict,
                    jump_host: str | None = None) -> dict | None:
        """Check disk usage. Returns alert dict if threshold exceeded."""
        code, stdout, stderr = self._ssh(
            hostname,
            "df -h --output=target,pcent,size,avail 2>/dev/null | tail -n +2",
            jump_host=jump_host,
        )
        if code != 0:
            return {"type": "disk", "level": "error", "message": f"SSH failed: {stderr}"}

        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            mount, pct_str = parts[0], parts[1].replace("%", "")
            try:
                pct = int(pct_str)
            except ValueError:
                continue

            if pct >= thresholds["disk_crit_pct"]:
                return {
                    "type": "disk",
                    "level": "critical",
                    "mount": mount,
                    "used_pct": pct,
                    "threshold": thresholds["disk_crit_pct"],
                    "raw_output": stdout,
                }
            elif pct >= thresholds["disk_warn_pct"]:
                return {
                    "type": "disk",
                    "level": "warning",
                    "mount": mount,
                    "used_pct": pct,
                    "threshold": thresholds["disk_warn_pct"],
                    "raw_output": stdout,
                }
        return None

    def _check_memory(self, hostname: str, thresholds: dict,
                      jump_host: str | None = None) -> dict | None:
        """Check memory usage. Returns alert dict if threshold exceeded."""
        code, stdout, stderr = self._ssh(
            hostname,
            "free -m | awk 'NR==2{print $2,$3,$7}'",
            jump_host=jump_host,
        )
        if code != 0:
            return {"type": "memory", "level": "error", "message": f"SSH failed: {stderr}"}

        parts = stdout.strip().split()
        if len(parts) < 3:
            return None

        total = int(parts[0])
        used = int(parts[1])
        available = int(parts[2])  # column $7 from free -m is the available MB

        used_pct = int((1 - available / total) * 100) if total > 0 else 0

        if used_pct >= thresholds["mem_crit_pct"]:
            # Pre-analysis: get top memory consumers
            code2, top_output, _ = self._ssh(
                hostname,
                "ps aux --sort=-%mem | head -6 | awk '{print $2,$11,$4\"%\"}'",
                jump_host=jump_host,
            )
            return {
                "type": "memory",
                "level": "critical",
                "used_pct": used_pct,
                "threshold": thresholds["mem_crit_pct"],
                "raw_output": stdout,
                "top_consumers": top_output.strip(),
            }
        elif used_pct >= thresholds["mem_warn_pct"]:
            code2, top_output, _ = self._ssh(
                hostname,
                "ps aux --sort=-%mem | head -6 | awk '{print $2,$11,$4\"%\"}'",
                jump_host=jump_host,
            )
            return {
                "type": "memory",
                "level": "warning",
                "used_pct": used_pct,
                "threshold": thresholds["mem_warn_pct"],
                "raw_output": stdout,
                "top_consumers": top_output.strip(),
            }
        return None

    def _check_cpu(self, server_id: str, hostname: str, thresholds: dict,
                   jump_host: str | None = None) -> dict | None:
        """Check CPU load. Uses sustained check logic."""
        code, stdout, stderr = self._ssh(
            hostname,
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1",
            jump_host=jump_host,
        )
        if code != 0:
            return None  # CPU check is best-effort

        try:
            cpu_pct = float(stdout.strip())
        except ValueError:
            return None

        warn_threshold = thresholds["cpu_warn_pct"]
        crit_threshold = thresholds["cpu_crit_pct"]
        sustained_needed = thresholds.get("cpu_sustained_checks", 3)

        if cpu_pct >= crit_threshold or cpu_pct >= warn_threshold:
            self._sustained_cpu[server_id] = self._sustained_cpu.get(server_id, 0) + 1
        else:
            self._sustained_cpu[server_id] = 0
            return None

        if self._sustained_cpu[server_id] < sustained_needed:
            return None

        # Pre-analysis: get top CPU consumers
        code2, top_output, _ = self._ssh(
            hostname,
            "ps aux --sort=-%cpu | head -6 | awk '{print $2,$11,$3\"%\"}'",
            jump_host=jump_host,
        )

        level = "critical" if cpu_pct >= crit_threshold else "warning"
        return {
            "type": "cpu",
            "level": level,
            "used_pct": cpu_pct,
            "threshold": crit_threshold if level == "critical" else warn_threshold,
            "sustained_checks": self._sustained_cpu[server_id],
            "top_consumers": top_output.strip(),
        }

    def _check_service(self, hostname: str, service: str,
                       jump_host: str | None = None) -> dict | None:
        """Check if a systemd service is active. Returns alert if not."""
        code, stdout, stderr = self._ssh(
            hostname, f"systemctl is-active {shlex.quote(service)}",
            jump_host=jump_host,
        )
        if code != 0 or stdout.strip() != "active":
            # Pre-analysis: grab last 20 journal lines
            code2, journal, _ = self._ssh(
                hostname,
                f"journalctl -u {shlex.quote(service)} --no-pager -n 20 2>/dev/null",
                jump_host=jump_host,
            )
            return {
                "type": "service",
                "level": "critical",
                "service": service,
                "status": stdout.strip() or "unknown",
                "journal_last_20": journal.strip(),
            }
        return None

    def _should_dispatch(self, server_id: str, alert: dict) -> bool:
        """Check whether an alert should be dispatched (dedup logic).

        Only dispatches if:
        - The alert is new (not seen before)
        - The severity level changed (warn -> crit or vice versa)
        - At least 6 check intervals have passed since the last dispatch
        """
        key = f"{server_id}:{alert.get('type', 'unknown')}"
        current_level = alert.get("level", "warning")
        last = self._last_alerts.get(key)

        if last is None:
            # First time seeing this alert for this server/type
            self._last_alerts[key] = {"level": current_level, "time": time.monotonic()}
            return True

        # Level changed — always dispatch
        if last["level"] != current_level:
            self._last_alerts[key] = {"level": current_level, "time": time.monotonic()}
            return True

        # Same level — check interval count
        elapsed = time.monotonic() - last["time"]
        intervals_passed = elapsed / self.config.check_interval
        if intervals_passed >= 6:
            self._last_alerts[key] = {"level": current_level, "time": time.monotonic()}
            return True

        return False

    def _dispatch_alert(self, server_id: str, hostname: str, alerts: list[dict]) -> None:
        """Dispatch alerts to the serveradmin agent via ask_agent_async."""
        summary = self._build_alert_summary(server_id, hostname, alerts)
        self._send_to_agent(summary)

    def _build_alert_summary(self, server_id: str, hostname: str, alerts: list[dict]) -> str:
        """Build a structured alert message for the agent."""
        lines = [
            f"[MONITOR ALERT] {server_id} ({hostname})",
            f"Time: {self._now()}",
            f"Alerts: {len(alerts)}",
            "",
        ]
        for i, alert in enumerate(alerts, 1):
            lines.append(f"--- Alert {i}: {alert['type']} [{alert['level'].upper()}] ---")
            for key, value in alert.items():
                if key in ("raw_output",):
                    continue  # skip raw output in summary, agent can request it
                if value and key != "level":
                    lines.append(f"  {key}: {value}")
            lines.append("")
        return "\n".join(lines)

    def _send_to_agent(self, message: str) -> None:
        """Send alert message to the serveradmin agent."""
        if not os.path.exists(ASK_AGENT_ASYNC):
            print(f"[{self._now()}] WARNING: ask_agent_async.py not found at {ASK_AGENT_ASYNC}", file=sys.stderr)
            return
        try:
            subprocess.run(
                ["python3", ASK_AGENT_ASYNC, "serveradmin", message],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as e:
            print(f"[{self._now()}] Failed to dispatch alert: {e}", file=sys.stderr)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Server Admin Monitoring Daemon")
    parser.add_argument(
        "--config",
        default="skills/ops_skill/config/thresholds.yaml",
        help="Path to thresholds config file",
    )
    parser.add_argument(
        "--ssh-key",
        default="/ductor/agents/serveradmin/workspace/.ssh/agent_key",
        help="Path to SSH private key",
    )
    parser.add_argument(
        "--ssh-user",
        default="agent",
        help="SSH username",
    )
    args = parser.parse_args()

    daemon = MonitorDaemon(
        config_path=args.config,
        ssh_key_path=args.ssh_key,
        ssh_user=args.ssh_user,
    )
    daemon.run()


if __name__ == "__main__":
    main()
