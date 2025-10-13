# UniRoam 🤖

> *Where UniPwn meets autonomous roaming*

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.8+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/Status-Research-red.svg" alt="Status">
</p>

**UniRoam** is an advanced autonomous robot worm framework for security research and red team operations. Built upon the [original UniPwn vulnerability research](https://github.com/Bin4ry/UniPwn), UniRoam demonstrates self-propagating malware capabilities targeting Unitree robotic platforms.

## 🎯 What is UniRoam?

UniRoam extends the original CVE research (CVE-2025-35027, CVE-2025-60017, CVE-2025-60250, CVE-2025-60251) into a complete wormable attack framework featuring:

- 🔄 **Autonomous Propagation** - Self-spreading via BLE and WiFi
- 🎮 **Command & Control** - Full C2 infrastructure with web dashboard
- 💾 **Multi-Stage Infection** - Sophisticated payload delivery system
- 🔐 **Operational Security** - Traffic encryption, evasion, anti-forensics
- 🧪 **Testing Framework** - Comprehensive simulation and benchmarking
- 🛡️ **Defensive Tools** - Detection rules, IOCs, incident response guides

## ⚠️ WARNING - Research Tool Only

**This is a RED TEAM RESEARCH TOOL.** Unauthorized use against systems you do not own is **illegal**. UniRoam is provided for:

✅ Security research in controlled environments  
✅ Red team training and exercises  
✅ Developing defensive countermeasures  
✅ Educational purposes  
✅ Authorized penetration testing  

❌ Unauthorized access or malicious attacks  

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/uniroam.git
cd uniroam

# Install dependencies
pip install -r requirements.txt

# Start C2 server
python c2_server.py

# Access dashboard at http://localhost:8443/
```

### Run Tests

```bash
# Full test suite
python test_worm.py --all

# Propagation simulation
python test_worm.py --simulate

# Performance benchmarks
python test_worm.py --benchmark
```

## 📚 Documentation

- **[Complete Framework Guide](README_WORM.md)** - Full documentation
- **[Defense Guide](DEFENSE_GUIDE.md)** - Detection, IOCs, and response
- **[Deployment Guide](DEPLOYMENT.md)** - Setup and usage instructions
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Technical overview

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│      UniRoam C2 Server              │
│  - REST API                         │
│  - Web Dashboard (Light/Dark/Hacker)│
│  - SQLite Database                  │
│  - Task Queue                       │
└───────────────┬─────────────────────┘
                │ HTTPS/DNS Tunnel
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐              ┌───▼────┐
│Robot 1 │◄────BLE─────►│Robot 2 │
│ Agent  │              │ Agent  │
└───┬────┘              └───┬────┘
    │                       │
    └───────WiFi────────────┘
        Autonomous Spread
```

## 🎨 C2 Dashboard Themes

UniRoam features a modern web dashboard with three beautiful themes:

- ☀️ **Light Mode** - Professional business interface
- 🌙 **Dark Mode** - Sleek modern dark theme
- 💀 **Hacker Mode** - Enhanced terminal aesthetic with CRT effects

![Dashboard Preview](images/dashboard_preview.png)

## 🔬 Key Features

### Autonomous Propagation
- BLE-based robot-to-robot infection
- WiFi network discovery and spreading
- Rate-limited stealth mode (5 infections/hour)
- Infection tracking to prevent loops

### Command & Control
- Real-time web dashboard
- Remote task execution
- Intelligence gathering
- Global control commands
- Statistics and metrics

### Persistence
- Systemd service installation
- Cron job backup
- RC.local modification
- Watchdog auto-restart
- Process name obfuscation

### Operational Security
- AES-GCM traffic encryption
- DNS tunneling fallback
- Sandbox detection & evasion
- Log cleaning
- Anti-forensics capabilities

## 📊 Performance

Based on benchmark results:

- **Encryption**: 100,000+ ops/sec
- **Packet Creation**: 200,000+ ops/sec
- **Payload Generation**: Sub-millisecond
- **Stage 0 Dropper**: 141 bytes (minimal footprint)

## 🛡️ Defensive Capabilities

UniRoam includes comprehensive defensive tools:

- **Detection Rules**: YARA, Suricata, Snort, Sigma, EQL
- **IOC Documentation**: File system, network, behavioral indicators
- **SIEM Queries**: Splunk and Elastic Stack ready
- **Incident Response**: Complete IR playbooks
- **Forensic Guides**: Memory, disk, and network analysis

## 🎓 Educational Value

UniRoam serves as a complete learning resource for:

- Modern malware architecture
- IoT/robotics security
- Red team operations
- Defensive security
- Worm propagation techniques
- C2 infrastructure design

## 📖 Original Research

UniRoam is built upon the groundbreaking research by:

- **Bin4ry** (Andreas Makris) - Lead Researcher
- **h0stile** (Kevin Finisterre) - Co-Author
- **legion1581** (Konstantin Severov) - PoC Contributor

**Research Paper**: [Cybersecurity AI: Humanoid Robots as Attack Vectors](https://arxiv.org/abs/2509.14139)

**Original CVEs**:
- [CVE-2025-35027](https://takeonme.org/cves/cve-2025-35027/)
- [CVE-2025-60017](https://cve.org/CVERecord?id=CVE-2025-60017)
- [CVE-2025-60250](https://cve.org/CVERecord?id=CVE-2025-60250)
- [CVE-2025-60251](https://cve.org/CVERecord?id=CVE-2025-60251)

## 🤝 Contributing

Contributions for defensive improvements are welcome:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/defense-improvement`)
3. Commit changes
4. Push to branch
5. Create Pull Request

**Focus areas**: Detection signatures, mitigation techniques, documentation improvements

## 📄 License

CC BY-NC-SA 4.0 (Non-Commercial, Share-Alike)

This project maintains the original licensing from the UniPwn research. See [LICENSE](LICENSE) for details.

## ⚖️ Legal Notice

This software is for authorized security research only. Unauthorized use may violate:
- Computer Fraud and Abuse Act (CFAA) - USA
- Computer Misuse Act - UK  
- Criminal Code - Canada
- Similar laws in other jurisdictions

**Always obtain explicit written permission before testing.**

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues (if published)
- **Research**: Contact original CVE researchers

## 🌟 Acknowledgments

- Original UniPwn research team
- Unitree Robotics (platform)
- Security research community
- Open source contributors

---

<p align="center">
  <strong>UniRoam - Advancing Robot Security Through Research</strong><br>
  <em>Built on UniPwn. Designed for Defense.</em>
</p>

---

**Version**: 1.0  
**Released**: January 2025  
**Status**: Production-Ready for Research Use

