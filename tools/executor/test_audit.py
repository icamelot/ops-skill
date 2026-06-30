import json
import os
import tempfile
import pytest
from tools.executor.audit import AuditLogger, get_audit_path


class TestAuditLogger:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.audit = AuditLogger(log_dir=self.tmpdir)

    def test_log_entry_writes_to_file(self):
        self.audit.log_entry(
            target="server-a",
            command="df -h",
            category="readonly",
            approved=True,
            result={"exit_code": 0, "stdout": "Filesystem ..."},
        )

        log_path = get_audit_path(self.tmpdir)
        assert os.path.exists(log_path)

        with open(log_path) as f:
            data = json.loads(f.readline())

        assert data["target"] == "server-a"
        assert data["command"] == "df -h"
        assert data["category"] == "readonly"
        assert data["approved"] is True
        assert data["exit_code"] == 0
        assert "timestamp" in data

    def test_multiple_entries_append(self):
        self.audit.log_entry(
            target="server-a", command="ls", category="readonly",
            approved=True, result={"exit_code": 0, "stdout": ""},
        )
        self.audit.log_entry(
            target="server-b", command="useradd x", category="modifying",
            approved=False, result={"exit_code": -1, "stdout": "REJECTED: no TOTP"},
        )

        log_path = get_audit_path(self.tmpdir)
        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2
        entries = [json.loads(line) for line in lines]
        assert entries[0]["target"] == "server-a"
        assert entries[1]["target"] == "server-b"
        assert entries[1]["approved"] is False

    def test_log_file_permissions_restrictive(self):
        self.audit.log_entry(
            target="server-a", command="ls", category="readonly",
            approved=True, result={"exit_code": 0, "stdout": ""},
        )
        log_path = get_audit_path(self.tmpdir)
        mode = os.stat(log_path).st_mode & 0o777
        assert mode == 0o600  # owner read/write only
