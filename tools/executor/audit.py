"""Audit logger — append-only command execution log."""

import json
import os
from datetime import datetime, timezone


AUDIT_FILENAME = "command_audit.jsonl"


def get_audit_path(log_dir: str) -> str:
    """Return the full path to the audit log file."""
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, AUDIT_FILENAME)


class AuditLogger:
    """Append-only audit log for all command executions.

    Each log entry is a JSON line containing:
    - timestamp (ISO 8601)
    - target server
    - command executed
    - category (readonly | modifying)
    - approved (bool)
    - exit_code, stdout, stderr (truncated)
    """

    def __init__(self, log_dir: str):
        self._log_path = get_audit_path(log_dir)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create log file with restrictive permissions if it doesn't exist."""
        if not os.path.exists(self._log_path):
            with open(self._log_path, "w") as f:
                f.write("")
            os.chmod(self._log_path, 0o600)

    def log_entry(
        self,
        target: str,
        command: str,
        category: str,
        approved: bool,
        result: dict,
    ) -> None:
        """Append an audit log entry.

        Args:
            target: Server hostname or identifier.
            command: The full command string that was (or would be) executed.
            category: 'readonly' or 'modifying'.
            approved: Whether the command was approved (TOTP or auto).
            result: Dict with keys: exit_code, stdout, stderr.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "command": command,
            "category": category,
            "approved": approved,
            "exit_code": result.get("exit_code"),
            "stdout": result.get("stdout", "")[:8192],
            "stderr": result.get("stderr", "")[:8192],
        }

        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
