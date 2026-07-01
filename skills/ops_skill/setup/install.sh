#!/bin/bash
# ops-skill container setup
# Run as root inside the Docker container (ductor-sub-serveradmin):
#   docker exec -u root ductor-sub-serveradmin bash /path/to/install.sh
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must run as root. Use: docker exec -u root ..."
    exit 1
fi

echo "=== ops-skill container setup ==="

# ---------- 1. system packages ----------
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    openssh-client \
    ntpsec \
    logrotate \
    supervisor \
    python3-pip

# ---------- 2. NTP time sync ----------
echo "[2/6] Configuring NTP..."
cat > /etc/ntpsec/ntp.conf << 'NTPCONF'
driftfile /var/lib/ntpsec/ntp.drift
pool pool.ntp.org iburst
restrict default kod nomodify notrap nopeer noquery
restrict 127.0.0.1
restrict ::1
NTPCONF
service ntpsec restart
echo "NTP status:"
ntpq -p || echo "NTP started (first sync may take a few minutes)"

# ---------- 3. Python dependencies ----------
echo "[3/6] Installing Python packages..."
pip3 install pyotp pyyaml

# ---------- 4. logrotate for audit logs ----------
echo "[4/6] Setting up logrotate..."
cat > /etc/logrotate.d/ops-skill-audit << 'LOGROTATE'
/ductor/agents/serveradmin/workspace/logs/command_audit.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0600 root root
    postrotate
        # Signal agent to reopen log if needed
        touch /ductor/agents/serveradmin/workspace/logs/.rotated
    endscript
}
/var/log/agent-shell-filter.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0600 root root
}
LOGROTATE

# ---------- 5. supervisor for monitor daemon ----------
echo "[5/6] Setting up supervisor..."
mkdir -p /var/log/supervisor
cat > /etc/supervisor/conf.d/ops-monitor.conf << 'SUPERVISOR'
[program:ops-monitor]
command=python3 /ductor/agents/serveradmin/workspace/skills/ops_skill/tools/monitor/monitor_daemon.py --config /ductor/agents/serveradmin/workspace/skills/ops_skill/config/thresholds.yaml --ssh-key /ductor/agents/serveradmin/workspace/.ssh/agent_key
directory=/ductor/agents/serveradmin/workspace
user=root
autostart=false
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/ductor/agents/serveradmin/workspace/logs/monitor-daemon.log
SUPERVISOR
supervisorctl reread
supervisorctl update || true

# ---------- 6. verify ----------
echo "[6/6] Verifying..."
echo "  SSH:   $(ssh -V 2>&1 | head -1 || echo 'NOT FOUND')"
echo "  pyOTP: $(python3 -c 'import pyotp; print(pyotp.__version__)' 2>/dev/null || echo 'NOT FOUND')"
echo "  YAML:  $(python3 -c 'import yaml; print(yaml.__version__)' 2>/dev/null || echo 'NOT FOUND')"
echo "  NTP:   $(ntpq -p 2>/dev/null | head -1 || echo 'checking...')"
echo "  Supervisor: $(supervisorctl version 2>/dev/null || echo 'checking...')"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Generate SSH key: ssh-keygen -t ed25519 -f .ssh/agent_key -C 'ops-skill'"
echo "  2. Deploy to target servers (see deploy.sh)"
echo "  3. Start monitor: supervisorctl start ops-monitor"
echo "  4. Edit thresholds: skills/ops_skill/config/thresholds.yaml"
