from unittest.mock import patch, MagicMock
from tools.executor.command_executor import CommandExecutor


class TestCommandExecutor:
    def setup_method(self):
        self.executor = CommandExecutor(
            ssh_key_path="/tmp/test_key",
            ssh_user="agent",
            max_modifying_per_hour=5,
        )

    def test_readonly_command_runs_directly(self):
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Filesystem  Size  Used Avail Use% Mounted on\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = self.executor.execute("server-a", "df -h")

            assert result["exit_code"] == 0
            assert result["approved"] is True  # auto-approved
            assert result["needs_approval"] is False
            assert mock_run.call_count == 1

    def test_modifying_command_without_totp_rejected(self):
        result = self.executor.execute("server-a", "systemctl restart nginx")

        assert result["exit_code"] == -1
        assert result["approved"] is False
        assert result["needs_approval"] is True
        assert "TOTP" in result.get("stderr", "")

    def test_modifying_command_with_totp_proceeds(self):
        # Any 6-digit code passes the client-side format check;
        # real validation happens server-side.
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Service restarted"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = self.executor.execute(
                "server-a", "systemctl restart nginx", totp_code="123456"
            )

            assert result["exit_code"] == 0
            assert mock_run.call_count == 1

    def test_chained_command_partially_modifying_requires_approval(self):
        result = self.executor.execute(
            "server-a", "ls -la && systemctl restart nginx"
        )
        assert result["needs_approval"] is True

    def test_injection_pattern_blocked(self):
        result = self.executor.execute("server-a", "echo $(whoami)")
        assert result["exit_code"] == -1
        assert result["blocked"] is True

    def test_rate_limit_exceeded(self):
        executor = CommandExecutor(
            ssh_key_path="/tmp/test_key",
            ssh_user="agent",
            max_modifying_per_hour=1,
        )

        # Use up the limit — any 6-digit code passes client-side format check
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "ok"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            executor.execute("server-a", "apt install htop", totp_code="123456")
            result = executor.execute("server-a", "apt install vim", totp_code="654321")

        assert result["exit_code"] == -1
        assert "rate" in result.get("stderr", "").lower()
