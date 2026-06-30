import pytest
from tools.executor.whitelist import classify_command, is_readonly


class TestClassifyCommand:
    # Read-only commands
    @pytest.mark.parametrize("cmd", [
        "df -h",
        "free -m",
        "uptime",
        "ps aux",
        "systemctl status nginx",
        "journalctl -u nginx --since '1 hour ago'",
        "cat /var/log/syslog",
        "ls -la /home",
        "who",
        "last -n 10",
        "ss -tlnp",
        "ip addr show",
        "du -sh /var/*",
        "top -bn1",
        "tail -n 100 /var/log/auth.log",
        "grep ERROR /var/log/app.log",
        "find /tmp -name '*.log'",
        "stat /etc/passwd",
        "dmesg | tail -20",
        "lsof -i :80",
        "id someuser",
        "getent passwd",
        "hostnamectl",
        "timedatectl",
        "uname -a",
    ])
    def test_readonly_commands(self, cmd):
        assert classify_command(cmd) == "readonly"
        assert is_readonly(cmd) is True

    # Modifying commands
    @pytest.mark.parametrize("cmd", [
        "systemctl restart nginx",
        "systemctl stop apache2",
        "systemctl start postgresql",
        "apt install htop",
        "apt remove nginx",
        "yum install httpd",
        "useradd newuser",
        "usermod -aG sudo newuser",
        "userdel olduser",
        "passwd someuser",
        "rm /tmp/file.txt",
        "rm -rf /tmp/cache",
        "chmod 755 /opt/app",
        "chown user:group /data",
        "iptables -A INPUT -p tcp --dport 80 -j ACCEPT",
        "systemctl enable nginx",
        "systemctl disable apache2",
        "dd if=/dev/zero of=/tmp/test bs=1M count=10",
        "mount /dev/sdb1 /mnt",
        "kill -9 1234",
        "shutdown -r now",
        "reboot",
    ])
    def test_modifying_commands(self, cmd):
        assert classify_command(cmd) == "modifying"
        assert is_readonly(cmd) is False

    def test_unknown_command_defaults_to_modifying(self):
        # Safety: unknown commands lean toward requiring approval
        assert classify_command("some-random-command --flag") == "modifying"
