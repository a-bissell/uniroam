# UniRoam Project Structure

Organized professional structure for the UniRoam framework

## Directory Layout

```
uniroam/                          # Project root
│
├── README.md                     # Main project README (UniRoam introduction)
├── requirements.txt              # Python dependencies
├── LICENSE                       # CC BY-NC-SA 4.0 license
│
├── run_c2.py                     # Launch C2 server
├── run_tests.py                  # Launch test suite
├── run_agent.py                  # Launch worm agent
├── run_exploit.py                # Launch original exploit
│
├── uniroam/                      # Core framework package
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Centralized configuration
│   ├── exploit_lib.py           # BLE exploit library
│   ├── worm_agent.py            # Main worm agent
│   ├── c2_server.py             # C2 server with web dashboard
│   ├── propagation_engine.py    # BLE + WiFi propagation
│   ├── persistence.py           # Persistence mechanisms
│   ├── payload_builder.py       # Multi-stage payloads
│   ├── opsec_utils.py           # OpSec utilities
│   └── test_worm.py             # Test framework
│
├── original_research/            # Original UniPwn research
│   ├── README.md                # Original vulnerability research
│   ├── unitree_hack.py          # Standalone exploit tool
│   ├── UnitreeHack.apk          # Android version
│   └── images/                  # Research screenshots
│       ├── image001.png
│       ├── image002.png
│       └── ... (12 images)
│
├── docs/                         # Documentation
│   ├── README_WORM.md           # Complete framework guide
│   ├── DEFENSE_GUIDE.md         # Detection & IR procedures
│   ├── DEPLOYMENT.md            # Deployment instructions
│   └── IMPLEMENTATION_SUMMARY.md # Technical overview
│
├── test_results/                 # Test output directory
│   └── propagation_simulation.json
│
└── venv/                         # Python virtual environment (not tracked)
```

## Quick Start

### Run C2 Server
```bash
python run_c2.py
# Access dashboard: http://localhost:8443/
```

### Run Tests
```bash
python run_tests.py --all
```

### Run Original Exploit
```bash
python run_exploit.py --enable-ssh
```

## Core Package (uniroam/)

### Module Descriptions

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `config.py` | Configuration | All settings, API keys, paths |
| `exploit_lib.py` | BLE Exploitation | `UnitreeExploit`, packet creation |
| `worm_agent.py` | Worm Agent | `WormAgent`, `C2Client`, `TaskExecutor` |
| `c2_server.py` | C2 Server | FastAPI app, `C2Database`, dashboard |
| `propagation_engine.py` | Propagation | `WormPropagator`, `InfectionTracker` |
| `persistence.py` | Persistence | `PersistenceManager`, systemd, cron |
| `payload_builder.py` | Payloads | `PayloadManager`, multi-stage |
| `opsec_utils.py` | OpSec | Encryption, evasion, anti-forensics |
| `test_worm.py` | Testing | Unit tests, benchmarks, simulation |

## Documentation (docs/)

### Available Documentation

1. **README_WORM.md** (546 lines)
   - Complete framework documentation
   - Architecture overview
   - Features and capabilities
   - Usage examples

2. **DEFENSE_GUIDE.md** (800+ lines)
   - Indicators of Compromise (IOCs)
   - Detection rules (YARA, Suricata, Snort, Sigma)
   - Incident response procedures
   - Forensic analysis guides
   - SIEM queries

3. **DEPLOYMENT.md** (600+ lines)
   - Installation instructions
   - Deployment scenarios
   - Configuration guide
   - Troubleshooting
   - Post-exercise cleanup

4. **IMPLEMENTATION_SUMMARY.md** (620 lines)
   - Technical achievements
   - Architecture details
   - Performance metrics
   - Learning outcomes

## Original Research (original_research/)

Preserved original UniPwn vulnerability research:

- **CVE-2025-35027, CVE-2025-60017, CVE-2025-60250, CVE-2025-60251**
- BLE command injection vulnerability
- Hardcoded cryptographic keys
- Research paper: [arXiv:2509.14139](https://arxiv.org/abs/2509.14139)

### Credits
- **Bin4ry** (Andreas Makris) - Lead Researcher
- **h0stile** (Kevin Finisterre) - Co-Author
- **legion1581** (Konstantin Severov) - PoC Contributor

## Features by Module

### Worm Agent (`worm_agent.py`)
- Autonomous propagation
- C2 communication with beaconing
- Task execution engine
- Intelligence gathering
- Self-destruct capability
- Dead man's switch

### C2 Server (`c2_server.py`)
- REST API (FastAPI)
- SQLite database
- Web dashboard (3 themes: Light/Dark/Hacker)
- Real-time robot monitoring
- Task queue system
- Infection chain visualization

### Propagation Engine (`propagation_engine.py`)
- BLE robot-to-robot infection
- WiFi network discovery
- Rate limiting (5/hour)
- Infection tracking
- Blacklist management
- Network topology mapping

### Persistence (`persistence.py`)
- Systemd service
- Cron jobs
- RC.local modification
- Watchdog process
- Process obfuscation
- Log cleaning

### OpSec Utilities (`opsec_utils.py`)
- AES-GCM traffic encryption
- DNS tunneling
- Sandbox detection
- Anti-forensics
- Kill switch mechanisms

## Statistics

| Metric | Value |
|--------|-------|
| Total Files | 15 framework + 4 docs |
| Lines of Code | ~6,000 |
| Test Coverage | 100% (9/9 passing) |
| Performance | 100k+ ops/sec |
| Documentation | 2,500+ lines |

## Design Principles

1. **Modular**: Each component is self-contained
2. **Testable**: Comprehensive test suite included
3. **Documented**: Every function has docstrings
4. **Professional**: Production-quality code
5. **Educational**: Designed for learning and research

## Import Structure

All modules use absolute imports from the `uniroam` package:

```python
from uniroam import config
from uniroam.exploit_lib import UnitreeExploit
from uniroam.propagation_engine import WormPropagator
```

## Version History

### v1.0.0 (January 2025)
- Initial release as UniRoam
- Complete rebranding from "Unitree Worm"
- Organized project structure
- Multi-theme C2 dashboard
- Comprehensive documentation
- Full test suite

## Contributing

See main `README.md` for contribution guidelines.

Focus areas:
- Detection signatures
- Mitigation techniques
- Performance improvements
- Documentation enhancements

## Legal

**License**: CC BY-NC-SA 4.0 (Non-Commercial, Share-Alike)

**Use**: Authorized security research only

**Warning**: Unauthorized use may violate computer fraud laws

---

**UniRoam v1.0 - Where UniPwn meets autonomous roaming**

