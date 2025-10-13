# 🤖 UniRoam Robot Simulator System

Test worm propagation without a fleet of physical robots!

## 🚀 Quick Start

### 1. Virtual Mode (Single Machine)

```bash
# Start C2 server
python run_c2.py

# In another terminal, launch 10 virtual robots
export VIRTUAL_BLE=true
python run_virtual_sim.py -n 10 --auto-infect SIM_000

# Watch propagation in C2 dashboard
# http://localhost:8443/
```

### 2. Distributed Mode (Multiple Devices)

```bash
# Deploy to Raspberry Pis
./deploy_sim_pi.sh pi@192.168.1.101 Go2 SIM_000 http://192.168.1.100:8443
./deploy_sim_pi.sh pi@192.168.1.102 G1 SIM_001 http://192.168.1.100:8443

# Start distributed simulation
python run_distributed_sim.py \
  --c2-url http://192.168.1.100:8443 \
  --config simulator_config.json
```

## 📁 Files Created

### Core Simulator
- `robot_simulator.py` - Emulates vulnerable Unitree robots
- `virtual_ble.py` - Software BLE emulation
- `command_sandbox.py` - Safe command execution
- `sim_coordinator.py` - Distributed coordination

### Launchers
- `run_virtual_sim.py` - Launch virtual swarm
- `run_distributed_sim.py` - Deploy across devices

### Deployment
- `deploy_sim_pi.sh` - Raspberry Pi deployment
- `Dockerfile.simulator` - Docker sandbox image

### Documentation
- `docs/SIMULATOR_GUIDE.md` - Complete usage guide (5000+ words)

### Configuration
- `uniroam/config.py` - Updated with simulator settings
- `uniroam/c2_server.py` - Enhanced with simulator tagging & visualization

## ✨ Features

### Realistic Emulation
- ✅ Full BLE protocol stack (AES-CFB128 encryption)
- ✅ Vulnerable command injection
- ✅ Chunked serial number responses
- ✅ Actually spawns worm agent when infected

### Flexible Deployment
- ✅ Virtual mode: 10-50 robots on one laptop
- ✅ Distributed mode: Scale across Raspberry Pis
- ✅ Hybrid mode: Mix real and simulated robots

### Safety
- ✅ Sandboxed execution (Docker or subprocess)
- ✅ Command blacklisting
- ✅ Isolated filesystems
- ✅ Network restrictions

### Observability
- ✅ C2 dashboard integration
- ✅ Visual differentiation (🤖 vs 🦿)
- ✅ Real-time infection tracking
- ✅ Propagation metrics

## 🎯 Use Cases

### 1. Testing Propagation Logic
```bash
python run_virtual_sim.py -n 20 --auto-infect SIM_000
# Watch: Does it spread? How fast? Rate limiting working?
```

### 2. C2 Resilience Testing
```bash
# Start 50 simulators, all beaconing to C2
python run_virtual_sim.py -n 50
# Monitor: C2 performance, database size, response times
```

### 3. Detection Rule Development
```bash
# Run simulators while monitoring network/process activity
# Develop IDS rules, YARA signatures, etc.
```

### 4. Operator Training
```bash
# Provide realistic C2 interface for red team training
# No physical robots needed!
```

## 🔧 Configuration

### Environment Variables

```bash
# Virtual BLE mode
export VIRTUAL_BLE=true

# Simulator count
export SIMULATOR_COUNT=10

# Sandbox type (docker, subprocess, none)
export SANDBOX_TYPE=subprocess

# C2 server
export C2_HOST=192.168.1.100
export C2_PORT=8443

# Debug mode
export WORM_DEBUG=true
```

### Simulator Config File

`simulator_config.json`:
```json
{
  "simulators": [
    {"host": "192.168.1.101", "port": 5555, "serial": "SIM_000", "model": "Go2"},
    {"host": "192.168.1.102", "port": 5555, "serial": "SIM_001", "model": "G1"},
    {"host": "192.168.1.103", "port": 5555, "serial": "SIM_002", "model": "B2"}
  ]
}
```

## 📊 Performance

| Mode | Robots/Device | CPU | RAM | Realism |
|------|---------------|-----|-----|---------|
| Virtual | 10-50 | 5% each | 50MB each | High |
| Distributed | 1-5 | 15% each | 100MB each | Very High |

## 🎨 C2 Dashboard

Simulators are visually differentiated:

```
┌─────────────────────────────────────────┐
│ Type │ Robot ID  │ Platform │ Status   │
├──────┼───────────┼──────────┼──────────┤
│ 🤖   │ SIM_000   │ Go2_SIM  │ active   │ ← Green highlight
│ 🤖   │ SIM_001   │ G1_SIM   │ active   │
│ 🦿   │ REAL_001  │ Go2      │ active   │ ← Normal
└─────────────────────────────────────────┘
```

## 📖 Documentation

See `docs/SIMULATOR_GUIDE.md` for:
- Complete setup instructions
- Testing scenarios
- Troubleshooting
- Advanced usage
- API reference

## 🧪 Testing

```bash
# Test sandbox
python command_sandbox.py

# Test virtual BLE
python virtual_ble.py

# Test single simulator
python robot_simulator.py --serial TEST_001

# Test full system
python run_virtual_sim.py -n 3 --interactive
```

## 🐛 Troubleshooting

### Issue: "Module not found"
```bash
pip install -r requirements.txt
```

### Issue: "Simulators not appearing in C2"
```bash
# Check C2 URL
echo $C2_HOST

# Verify C2 is running
curl http://localhost:8443/api/v1/status
```

### Issue: "Permission denied" on deploy
```bash
chmod +x deploy_sim_pi.sh
```

## 🔒 Security

⚠️ **For controlled testing only!**

- Run in isolated network
- Use strong C2 passwords
- Review sandbox logs
- Clean up after testing

## 📈 Roadmap

Future enhancements:
- [ ] GUI for simulator management
- [ ] Propagation visualization (D3.js graph)
- [ ] Automated testing scenarios
- [ ] Performance benchmarking suite
- [ ] Multi-network simulation

## 🤝 Contributing

Improvements welcome:
- More realistic BLE timing
- Additional robot models
- Enhanced sandbox isolation
- Better visualization

## 📄 License

CC BY-NC-SA 4.0 (Non-Commercial, Share-Alike)

---

**UniRoam v1.0 - Where UniPwn meets autonomous roaming**  
*Simulator Edition*

