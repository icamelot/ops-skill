import pytest
from tools.executor.command_parser import (
    parse_command,
    validate_commands,
    CommandSecurityError,
)


class TestParseCommand:
    def test_simple_command(self):
        assert parse_command("ls -la") == ["ls -la"]

    def test_chained_with_double_ampersand(self):
        result = parse_command("ls -la && echo done")
        assert result == ["ls -la", "echo done"]

    def test_chained_with_semicolon(self):
        result = parse_command("ls -la; whoami")
        assert result == ["ls -la", "whoami"]

    def test_chained_with_pipe(self):
        result = parse_command("cat file | grep foo")
        assert result == ["cat file | grep foo"]

    def test_empty_command_returns_empty_list(self):
        assert parse_command("") == []

    def test_strips_whitespace(self):
        result = parse_command("  df -h  &&   free -m  ")
        assert result == ["df -h", "free -m"]


class TestValidateCommands:
    def test_safe_commands_pass(self):
        ok, reason = validate_commands(["ls -la", "df -h"])
        assert ok is True
        assert reason == ""

    def test_dollar_paren_blocked(self):
        ok, reason = validate_commands(["echo $(whoami)"])
        assert ok is False
        assert "$()" in reason

    def test_backtick_blocked(self):
        ok, reason = validate_commands(["echo `whoami`"])
        assert ok is False
        assert "backtick" in reason

    def test_eval_blocked(self):
        ok, reason = validate_commands(["eval ls"])
        assert ok is False
        assert "eval" in reason

    def test_exec_blocked(self):
        ok, reason = validate_commands(["exec bash"])
        assert ok is False
        assert "exec" in reason

    def test_io_redirect_to_dev_blocked(self):
        ok, reason = validate_commands(["cat foo > /dev/sda"])
        assert ok is False

    def test_multiple_commands_one_blocked(self):
        ok, reason = validate_commands(["ls -la", "eval rm -rf /"])
        assert ok is False

    def test_command_with_shell_var_expansion_allowed(self):
        ok, reason = validate_commands(["echo $HOME"])
        assert ok is True

    def test_redirect_to_file_allowed(self):
        ok, reason = validate_commands(["echo hello > /tmp/out.txt"])
        assert ok is True
