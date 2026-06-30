#!/usr/bin/env python3
"""Enqueue a notification for the main agent's user.

Sub-agents use this to request that a message be pushed to the user.
A watchdog cron job on the main agent picks it up and sends it via Telegram.

Usage:
    python3 enqueue_notification.py "Server admin" "磁盘使用率超过 90%"
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: enqueue_notification.py <from_name> <message>", file=sys.stderr)
        sys.exit(1)

    from_name = sys.argv[1]
    text = sys.argv[2]

    ductor_home = Path(os.environ.get("DUCTOR_HOME", Path.home() / ".ductor"))
    # Always resolve to the ROOT ductor home (not sub-agent's agents/<name>/)
    if ductor_home.parent.name == "agents":
        ductor_home = ductor_home.parent.parent
    queue_path = ductor_home / ".user_notification_queue.json"

    # Read existing
    entries = []
    if queue_path.exists():
        try:
            entries = json.loads(queue_path.read_text())
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        "from": from_name,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    queue_path.write_text(json.dumps(entries, ensure_ascii=False))
    print(f"OK: notification queued from {from_name}")


if __name__ == "__main__":
    main()
