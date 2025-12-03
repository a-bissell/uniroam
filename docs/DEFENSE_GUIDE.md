# Defensive Guide: Unitree Worm Detection & Response

## Executive Summary

This document provides comprehensive guidance for detecting, analyzing, and responding to Unitree worm infections. It is intended for security operations teams, incident responders, and system administrators responsible for Unitree robot deployments.

## Table of Contents

1. [Indicators of Compromise (IOCs)](#indicators-of-compromise-iocs)
2. [Detection Rules](#detection-rules)
3. [Incident Response Procedures](#incident-response-procedures)
4. [Forensic Analysis](#forensic-analysis)
5. [Prevention & Hardening](#prevention--hardening)
6. [Monitoring & Alerting](#monitoring--alerting)

## Indicators of Compromise (IOCs)

### File System Artifacts

#### Primary Infection Files
```
/usr/local/bin/unitree-updater          # Main worm executable
/usr/local/bin/unitree-watchdog         # Persistence watchdog
/etc/systemd/system/unitree-service.service
/etc/unitree/.config                    # Worm configuration
/var/log/unitree-service.log           # Worm logs
```

#### Temporary Files
```
/tmp/.unitree_targets                  # Infection tracking DB
/tmp/.unitree_blacklist                # Failed infection attempts
```

#### Database Files
```
unitree_devices.db                     # Original exploit DB
worm_c2.db                            # C2 server database
```

### File Hashes (SHA256)

```
# These would be actual hashes in production
unitree-updater:        [compute from actual file]
unitree-watchdog:       [compute from actual file]
unitree-service.service: [compute from actual file]
```

### Network Indicators

#### C2 Communication Patterns
```
Protocol:       HTTPS (443) or HTTP (8443)
Endpoints:      /api/v1/beacon
                /api/v1/tasks/{robot_id}
                /api/v1/report
                /api/v1/payload/stage1
                /api/v1/payload/full

Beacon Interval: 60-300 seconds (randomized)
User-Agents:    - Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36...
                - curl/7.68.0
                - python-requests/2.31.0
                - (Randomized)

HTTP Headers:   X-API-Key: [varies per deployment]
```

#### DNS Indicators
```
DNS Tunneling Pattern:
- Long subdomain labels (up to 63 chars)
- Hexadecimal characters in subdomains
- Multiple subdomain levels
- Queries to: *.unitree.com (fake domain for tunneling)
```

#### BLE Indicators
```
Service UUID:   0000ffe0-0000-1000-8000-00805f9b34fb
Write Char:     0000ffe2-0000-1000-8000-00805f9b34fb
Notify Char:    0000ffe1-0000-1000-8000-00805f9b34fb

Characteristics:
- Encrypted traffic (AES-CFB128)
- Hardcoded key: df98b715d5c6ed2b25817b6f2554124a
- Hardcoded IV:  2841ae97419c2973296a0d4bdfe19a4f
```

### Process Indicators

#### Process Names (Obfuscated)
```
[kworker/0:1]           # Fake kernel worker
systemd-udevd          # Fake udev daemon
systemd-journald       # Fake journal daemon
rsyslogd              # Fake syslog daemon
dbus-daemon           # Fake D-Bus daemon
```

#### Command Line Patterns
```
/usr/bin/python3 /usr/local/bin/unitree-updater
python3 -c "import urllib.request..."
python3 -c "import gzip,base64;exec..."
bash -c '";$(command);#'
```

#### Process Behavior
- Python process with BLE libraries loaded
- Continuous network activity to single external IP
- Regular beacon pattern (60-300s intervals)
- Child processes spawned for infections

### Registry/Configuration Indicators

#### Systemd Service
```ini
[Unit]
Description=Unitree Robot System Service
After=network.target bluetooth.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/unitree-updater
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

#### Cron Entries
```cron
*/15 * * * * /usr/bin/python3 /usr/local/bin/unitree-updater >/dev/null 2>&1
```

#### RC Local Modifications
```bash
/usr/bin/python3 /usr/local/bin/unitree-updater &
```

### Behavioral Indicators

1. **Unusual BLE Activity**
   - Continuous BLE scanning
   - Connections to multiple Unitree robots
   - Encrypted BLE traffic with known service UUIDs

2. **Network Anomalies**
   - Regular HTTPS beacons to non-Unitree domains
   - DNS queries with unusual patterns
   - Network scanning activity (nmap signatures)

3. **System Modifications**
   - New systemd services
   - Modified crontab
   - Cleared/modified log files
   - Gaps in auth.log, syslog timestamps

4. **Resource Usage**
   - Low CPU process with high network I/O
   - Persistent Python processes
   - Multiple concurrent BLE connections

## Detection Rules

### YARA Rules

```yara
rule Unitree_Worm_Payload
{
    meta:
        description = "Detects Unitree worm payload patterns"
        author = "Security Research Team"
        date = "2025-01-13"
        severity = "critical"
    
    strings:
        $aes_key = "df98b715d5c6ed2b25817b6f2554124a"
        $aes_iv = "2841ae97419c2973296a0d4bdfe19a4f"
        $handshake = "unitree" ascii
        $c2_endpoint1 = "/api/v1/beacon" ascii
        $c2_endpoint2 = "/api/v1/tasks" ascii
        $persistence1 = "unitree-service" ascii
        $persistence2 = "/usr/local/bin/unitree-updater" ascii
        $ble_service = "0000ffe0-0000-1000-8000-00805f9b34fb" ascii
        
    condition:
        ($aes_key and $aes_iv) or
        (2 of ($c2_endpoint*)) or
        (2 of ($persistence*)) or
        ($ble_service and $handshake)
}

rule Unitree_Worm_Dropper
{
    meta:
        description = "Detects Unitree worm dropper stage"
        severity = "critical"
    
    strings:
        $dropper1 = "python3 -c \"import urllib.request" ascii
        $dropper2 = "exec(urllib.request.urlopen(" ascii
        $dropper3 = "/api/v1/payload/stage1" ascii
        $dropper4 = "import gzip,base64;exec(gzip.decompress" ascii
        
    condition:
        2 of them
}
```

### Suricata Rules

```
# C2 Communication Detection
alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"Unitree Worm C2 Beacon"; \
    flow:established,to_server; content:"/api/v1/beacon"; http_uri; \
    content:"X-API-Key"; http_header; \
    threshold:type both, track by_src, count 3, seconds 600; \
    classtype:trojan-activity; sid:1000001; rev:1;)

alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"Unitree Worm Payload Download"; \
    flow:established,to_server; content:"/api/v1/payload/"; http_uri; \
    classtype:trojan-activity; sid:1000002; rev:1;)

# DNS Tunneling Detection
alert dns $HOME_NET any -> any 53 (msg:"Unitree Worm DNS Tunneling"; \
    dns_query; content:"unitree.com"; nocase; \
    pcre:"/[0-9a-f]{40,}/i"; \
    classtype:trojan-activity; sid:1000003; rev:1;)
```

### Snort Rules

```
# BLE Traffic Anomaly
alert tcp $HOME_NET any -> $EXTERNAL_NET any (msg:"Unitree Worm BLE Exploit Traffic"; \
    content:"|52|"; depth:1; content:"|51|"; distance:0; \
    classtype:attempted-admin; sid:2000001; rev:1;)

# Command Injection Pattern
alert tcp $HOME_NET any -> $EXTERNAL_NET any (msg:"Unitree Worm Command Injection"; \
    content:"\";$("; nocase; content:");#"; distance:0; \
    classtype:web-application-attack; sid:2000002; rev:1;)
```

### Sigma Rules

```yaml
title: Unitree Worm Systemd Service Installation
status: experimental
description: Detects installation of Unitree worm systemd service
references:
    - https://github.com/yourrepo/unipwn
tags:
    - attack.persistence
    - attack.t1543.002
logsource:
    product: linux
    service: auditd
detection:
    selection:
        type: 'SYSCALL'
        syscall: 'openat'
        name|contains: '/etc/systemd/system/unitree'
    condition: selection
falsepositives:
    - Legitimate Unitree system services
level: critical
```

### Elastic (EQL) Rules

```
// Unitree Worm Process Execution
process where process.name == "python3" and 
  process.args : "*unitree-updater*"

// Unitree Worm Persistence via Cron
file where file.path : "/var/spool/cron/crontabs/*" and
  file.extension == "cron" and
  process.name == "crontab" and
  file.content : "*unitree*"

// Unitree Worm Network Beaconing
network where network.protocol == "http" and
  http.request.uri.path : "/api/v1/beacon" and
  destination.ip != "10.0.0.0/8" and
  destination.ip != "172.16.0.0/12" and
  destination.ip != "192.168.0.0/16"
```

## Incident Response Procedures

### Phase 1: Detection & Triage (0-15 minutes)

#### Initial Assessment
```bash
# 1. Check for active worm processes
ps aux | grep -E 'unitree|python3.*urllib' | grep -v grep

# 2. Check for persistence mechanisms
systemctl list-units | grep unitree
crontab -l | grep unitree
cat /etc/rc.local | grep unitree

# 3. Check network connections
netstat -antp | grep ESTABLISHED | grep python3

# 4. Check for worm files
ls -la /usr/local/bin/unitree*
ls -la /tmp/.unitree*
```

#### Severity Classification
- **Critical**: Active C2 communication, active propagation
- **High**: Persistence installed, no active C2
- **Medium**: Failed infection attempts detected

### Phase 2: Containment (15-30 minutes)

#### Network Isolation
```bash
# 1. Block C2 communication (identify C2 IP from netstat)
iptables -A OUTPUT -d <C2_IP> -j DROP

# 2. Disable BLE
systemctl stop bluetooth
systemctl disable bluetooth

# 3. Disconnect WiFi
ifconfig wlan0 down

# 4. Isolate on network (notify network team)
# Move to quarantine VLAN if available
```

#### Process Termination
```bash
# 1. Kill worm processes
pkill -9 -f unitree-updater
pkill -9 -f unitree-watchdog

# 2. Stop services
systemctl stop unitree-service

# 3. Verify termination
ps aux | grep unitree
```

### Phase 3: Eradication (30-60 minutes)

#### Remove Persistence
```bash
# 1. Remove systemd service
systemctl disable unitree-service
rm -f /etc/systemd/system/unitree-service.service
systemctl daemon-reload

# 2. Clean crontab
crontab -e  # Manually remove unitree entries
# Or automated:
crontab -l | grep -v unitree | crontab -

# 3. Clean rc.local
sed -i '/unitree/d' /etc/rc.local

# 4. Remove files
rm -rf /usr/local/bin/unitree*
rm -rf /etc/unitree/
rm -rf /tmp/.unitree*
rm -f /var/log/unitree-service.log
```

#### Secure Deletion
```bash
# Use shred for secure deletion
shred -vfz -n 3 /usr/local/bin/unitree-updater
shred -vfz -n 3 /usr/local/bin/unitree-watchdog
```

### Phase 4: Recovery (60+ minutes)

#### System Restoration
```bash
# 1. Update firmware (if patched)
# Follow Unitree update procedures

# 2. Change credentials
passwd root
# Change WiFi passwords
# Rotate SSH keys

# 3. Restore from clean backup (if available)
# Or perform factory reset

# 4. Reboot
reboot
```

#### Verification
```bash
# After reboot, verify clean state
ps aux | grep unitree
systemctl list-units | grep unitree
crontab -l
netstat -antp
```

### Phase 5: Post-Incident (Ongoing)

#### Documentation
- Timeline of infection
- Infection vector
- Data accessed/exfiltrated
- Other affected systems

#### Lessons Learned
- How was robot infected?
- What detection gaps exist?
- What preventive measures needed?

## Forensic Analysis

### Memory Analysis

```bash
# 1. Capture memory dump (if forensic tools available)
sudo insmod lime.ko "path=/tmp/memory.lime format=lime"

# 2. Analyze with Volatility
volatility -f memory.lime --profile=LinuxUbuntu_5_4_0x64 linux_pslist
volatility -f memory.lime --profile=LinuxUbuntu_5_4_0x64 linux_netstat

# 3. Extract Python artifacts
strings memory.lime | grep -E 'unitree|c2|beacon'
```

### Disk Forensics

```bash
# 1. Create forensic image
dd if=/dev/sda of=/mnt/evidence/robot_disk.img bs=4M status=progress

# 2. Mount read-only
mount -o ro,loop robot_disk.img /mnt/analysis

# 3. Extract artifacts
find /mnt/analysis -name "*unitree*"
find /mnt/analysis -type f -mtime -7  # Files modified in last week

# 4. Timeline analysis
fls -r -m / robot_disk.img > timeline.body
mactime -b timeline.body -d > timeline.csv
```

### Network Forensics

```bash
# 1. Analyze packet captures
tcpdump -r capture.pcap -A | grep -E 'unitree|beacon|payload'

# 2. Extract HTTP traffic
tshark -r capture.pcap -Y "http" -T fields \
  -e ip.src -e ip.dst -e http.request.uri -e http.user_agent

# 3. Identify C2 server
tshark -r capture.pcap -Y "http.request.uri contains beacon" \
  -T fields -e ip.dst | sort -u
```

### Log Analysis

```bash
# 1. Check authentication logs
grep -E 'unitree|ssh.*root|Failed password' /var/log/auth.log

# 2. Check system logs
grep -E 'unitree|systemd.*service' /var/log/syslog

# 3. Check BLE/Bluetooth logs
journalctl -u bluetooth | grep -E 'connect|disconnect'

# 4. Identify log tampering
# Look for gaps in timestamps
# Check file modification times vs. log entry times
ls -la /var/log/ | grep -E 'auth.log|syslog'
```

### Artifact Collection Script

```bash
#!/bin/bash
# artifact_collector.sh

EVIDENCE_DIR="/tmp/unitree_evidence_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EVIDENCE_DIR"

echo "[+] Collecting Unitree worm artifacts..."

# Process information
ps aux > "$EVIDENCE_DIR/processes.txt"
ps aux | grep -E 'unitree|python' > "$EVIDENCE_DIR/suspicious_processes.txt"

# Network connections
netstat -antp > "$EVIDENCE_DIR/network_connections.txt"
ss -tulpn > "$EVIDENCE_DIR/listening_ports.txt"

# Files
find / -name "*unitree*" 2>/dev/null > "$EVIDENCE_DIR/unitree_files.txt"
ls -laR /usr/local/bin/ > "$EVIDENCE_DIR/usr_local_bin.txt"
ls -laR /etc/systemd/system/ > "$EVIDENCE_DIR/systemd_services.txt"

# Persistence
systemctl list-units --all > "$EVIDENCE_DIR/systemd_units.txt"
crontab -l > "$EVIDENCE_DIR/crontab.txt" 2>/dev/null
cat /etc/rc.local > "$EVIDENCE_DIR/rc_local.txt" 2>/dev/null

# Logs
cp /var/log/auth.log* "$EVIDENCE_DIR/"
cp /var/log/syslog* "$EVIDENCE_DIR/"
journalctl -u bluetooth > "$EVIDENCE_DIR/bluetooth.log"

# Configuration
ip addr > "$EVIDENCE_DIR/network_config.txt"
ip route > "$EVIDENCE_DIR/routing_table.txt"

# Create tarball
tar czf "${EVIDENCE_DIR}.tar.gz" "$EVIDENCE_DIR"
echo "[+] Evidence collected: ${EVIDENCE_DIR}.tar.gz"
```

## Prevention & Hardening

### Immediate Hardening Steps

#### 1. Disable BLE WiFi Configuration
```python
# Patch the BLE service to disable WiFi config
# This would require Unitree to provide a patch
# Workaround: Disable BLE service entirely if not needed
systemctl disable bluetooth
```

#### 2. Network Segmentation
```bash
# Isolate robots on dedicated VLAN
# Example iptables rules:

# Block outbound traffic except to specific IPs
iptables -P OUTPUT DROP
iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT        # Internal network
iptables -A OUTPUT -d <UNITREE_UPDATE_SERVER> -j ACCEPT  # Legitimate updates
iptables -A OUTPUT -o lo -j ACCEPT                 # Localhost

# Block BLE-related traffic from leaving local network
iptables -A OUTPUT -p tcp --dport 8080:8090 -j DROP
```

#### 3. Application Whitelisting
```bash
# Allow only approved executables
# Using AppArmor or SELinux

# AppArmor profile for robot processes
cat > /etc/apparmor.d/unitree.robot <<EOF
#include <tunables/global>

/opt/unitree/bin/* {
  #include <abstractions/base>
  
  # Deny network access for robot binaries
  deny network inet,
  deny network inet6,
  
  # Deny BLE access
  deny /dev/bluetooth rw,
  
  # Allow only necessary file access
  /opt/unitree/** r,
  /tmp/robot_* rw,
}
EOF

apparmor_parser -r /etc/apparmor.d/unitree.robot
```

### Long-Term Security Measures

#### 1. Cryptographic Key Rotation
```
Problem: Hardcoded AES keys
Solution: Implement per-device unique keys
         Vendor must provide firmware update
```

#### 2. Input Validation
```python
# Pseudocode for proper input validation
def set_wifi_ssid(ssid):
    # Validate SSID
    if not re.match(r'^[a-zA-Z0-9_-]{1,32}$', ssid):
        raise ValueError("Invalid SSID format")
    
    # Sanitize for shell
    safe_ssid = shlex.quote(ssid)
    
    # Use parameterized command
    subprocess.run(['nmcli', 'connection', 'modify', 'wifi', 'ssid', safe_ssid])
```

#### 3. Secure Boot & Firmware Verification
```bash
# Implement secure boot chain
# Verify firmware signatures before execution
# Require signed updates only
```

#### 4. Runtime Integrity Monitoring
```bash
# Use AIDE or Tripwire to monitor file integrity
aide --init
aide --check

# Monitor for unauthorized changes
```

## Monitoring & Alerting

### SIEM Integration

#### Splunk Queries
```spl
# Detect worm C2 beaconing
index=firewall sourcetype=firewall_traffic
| where like(uri_path, "%/api/v1/beacon%")
| stats count by src_ip, dest_ip
| where count > 10

# Detect BLE anomalies
index=bluetooth
| stats count by src_mac, dest_mac, service_uuid
| where service_uuid="0000ffe0-0000-1000-8000-00805f9b34fb"

# Detect persistence installation
index=linux sourcetype=syslog "systemd" "unitree"
| table _time, host, message
```

#### Elastic Stack (ELK) Queries
```json
{
  "query": {
    "bool": {
      "should": [
        {
          "match_phrase": {
            "process.command_line": "unitree-updater"
          }
        },
        {
          "match": {
            "url.path": "/api/v1/beacon"
          }
        },
        {
          "match": {
            "file.path": "/etc/systemd/system/unitree-service.service"
          }
        }
      ],
      "minimum_should_match": 1
    }
  }
}
```

### Automated Response Playbooks

#### Playbook 1: Worm Detection → Isolation
```yaml
# Ansible playbook for automated response
---
- name: Unitree Worm Incident Response
  hosts: infected_robots
  become: yes
  
  tasks:
    - name: Stop worm processes
      shell: pkill -9 -f unitree
      ignore_errors: yes
    
    - name: Disable networking
      systemd:
        name: "{{ item }}"
        state: stopped
      loop:
        - bluetooth
        - NetworkManager
    
    - name: Remove persistence
      file:
        path: "{{ item }}"
        state: absent
      loop:
        - /usr/local/bin/unitree-updater
        - /etc/systemd/system/unitree-service.service
    
    - name: Notify SOC
      uri:
        url: https://soc.company.com/api/incident
        method: POST
        body_format: json
        body:
          severity: critical
          title: "Unitree Worm Detected"
          host: "{{ inventory_hostname }}"
```

### Continuous Monitoring

```bash
# Deploy osquery for continuous monitoring
# osquery.conf
{
  "schedule": {
    "unitree_processes": {
      "query": "SELECT * FROM processes WHERE name LIKE '%unitree%' OR cmdline LIKE '%unitree%';",
      "interval": 60
    },
    "unitree_files": {
      "query": "SELECT * FROM file WHERE path LIKE '/usr/local/bin/unitree%';",
      "interval": 300
    },
    "suspicious_cron": {
      "query": "SELECT * FROM crontab WHERE command LIKE '%unitree%';",
      "interval": 300
    },
    "network_connections": {
      "query": "SELECT * FROM process_open_sockets WHERE remote_port IN (8443, 443) AND remote_address NOT LIKE '10.%';",
      "interval": 60
    }
  }
}
```

## Threat Hunting

### Hunt Hypothesis 1: Dormant Infections

**Hypothesis**: Infected robots may be dormant, waiting for C2 to come online

**Hunt Procedure**:
```bash
# Look for persistence without active process
for host in $(cat robot_inventory.txt); do
  ssh $host "systemctl list-units | grep unitree && ! pgrep -f unitree" \
    && echo "$host: DORMANT INFECTION FOUND"
done
```

### Hunt Hypothesis 2: Failed Infection Attempts

**Hypothesis**: Failed infections leave traces in logs

**Hunt Procedure**:
```bash
# Search for BLE connection anomalies
journalctl -u bluetooth --since "24 hours ago" | grep -E 'connect|disconnect' \
  | awk '{print $3}' | sort | uniq -c | sort -nr
# High connection counts may indicate infection attempts
```

### Hunt Hypothesis 3: Lateral Movement

**Hypothesis**: Worm spreads across network segments

**Hunt Procedure**:
```spl
# Splunk query for network propagation
index=firewall 
| stats dc(dest_ip) as unique_dests by src_ip
| where unique_dests > 10
| table src_ip, unique_dests
```

## Checklist: Post-Incident Hardening

- [ ] All infected robots identified and remediated
- [ ] Network segmentation implemented
- [ ] BLE services disabled or restricted
- [ ] Firmware updated (if patch available)
- [ ] All credentials rotated
- [ ] SIEM rules deployed
- [ ] IDS/IPS signatures updated
- [ ] Application whitelisting enabled
- [ ] File integrity monitoring active
- [ ] Incident report completed
- [ ] Lessons learned documented
- [ ] Security awareness training updated

## Escalation Contacts

### Internal
- **SOC**: soc@company.com / +1-555-SOC-TEAM
- **Incident Response**: ir@company.com
- **Network Security**: netsec@company.com

### External
- **Unitree Support**: (Document shows no response)
- **CERT/CC**: cert@cert.org
- **FBI IC3**: https://www.ic3.gov/

## Additional Resources

- [MITRE ATT&CK - Persistence](https://attack.mitre.org/tactics/TA0003/)
- [NIST Incident Response Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
- [SANS Incident Response](https://www.sans.org/posters/incident-response-poster/)
- [BLE Security](https://www.bluetooth.com/learn-about-bluetooth/key-attributes/bluetooth-security/)

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-13  
**Next Review**: 2025-04-13

