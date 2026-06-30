"""Whitelist router — classifies commands as read-only or modifying."""

import re
from typing import Literal

CommandCategory = Literal["readonly", "modifying"]


# Read-only patterns: commands safe to auto-approve
READONLY_PATTERNS: list[str] = [
    # Filesystem inspection
    r"^ls\b", r"^ll\b", r"^dir\b",
    r"^df\b", r"^du\b", r"^stat\b",
    r"^cat\b", r"^head\b", r"^tail\b",
    r"^less\b", r"^zcat\b", r"^zless\b",
    r"^file\b",
    # Search / find (read-only)
    r"^find\b", r"^locate\b", r"^grep\b", r"^egrep\b",
    r"^zgrep\b",
    # System inspection
    r"^ps\b", r"^top\b", r"^htop\b", r"^uptime\b",
    r"^free\b", r"^vmstat\b", r"^iostat\b",
    r"^dmesg\b", r"^lsof\b", r"^fdisk\s+-l\b",
    r"^lsblk\b", r"^blkid\b",
    # systemctl (status only)
    r"^systemctl\s+status\b", r"^systemctl\s+list-\b",
    r"^systemctl\s+is-\b", r"^systemctl\s+show\b",
    r"^systemctl\s+cat\b",
    # journalctl (read-only)
    r"^journalctl\b",
    # User inspection
    r"^who\b", r"^w\b", r"^whoami\b", r"^id\b",
    r"^last\b", r"^lastb\b", r"^lastlog\b",
    r"^getent\b", r"^groups\b",
    # Network inspection
    r"^ss\b", r"^netstat\b", r"^ip\s+addr\b",
    r"^ip\s+link\b", r"^ip\s+route\b", r"^ip\s+neigh\b",
    r"^hostname\b", r"^hostnamectl\b",
    r"^ping\b", r"^traceroute\b", r"^nslookup\b",
    r"^dig\b", r"^curl\b", r"^wget\b",
    # System info
    r"^uname\b", r"^lscpu\b", r"^lspci\b", r"^lsusb\b",
    r"^timedatectl\b", r"^localectl\b",
    # Process inspection
    r"^pgrep\b", r"^pidof\b",
    # Package inspection
    r"^dpkg\s+-[lL]\b", r"^rpm\s+-q[a-z]*\b",
    r"^apt\s+list\b", r"^apt-cache\b",
    # Disk / filesystem
    r"^findmnt\b",
    # Log viewing
    r"^loginctl\s+list-\b", r"^loginctl\s+show-\b",
    # Environment
    r"^env\b", r"^printenv\b", r"^echo\b",
    # Help / version
    r"--help$", r"--version$", r"-h$",
    r"^man\b", r"^info\b", r"^whatis\b",
    # Docker read-only
    r"^docker\s+ps\b", r"^docker\s+images\b",
    r"^docker\s+logs\b", r"^docker\s+inspect\b",
    r"^docker\s+stats\b",
]


def classify_command(command: str) -> CommandCategory:
    """Classify a single command as 'readonly' or 'modifying'.

    Matches against known read-only patterns. If no pattern matches,
    defaults to 'modifying' (safe fail).
    """
    cmd = command.strip()

    for pattern in READONLY_PATTERNS:
        if re.search(pattern, cmd):
            return "readonly"

    return "modifying"


def is_readonly(command: str) -> bool:
    """Return True if the command is classified as read-only."""
    return classify_command(command) == "readonly"
