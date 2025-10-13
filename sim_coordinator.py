#!/usr/bin/env python3
"""
Distributed Simulator Coordinator
Orchestrates robot simulators across multiple physical devices
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from uniroam import config

@dataclass
class SimulatorNode:
    """Represents a simulator running on a physical device"""
    host: str
    port: int
    robot_id: str
    model: str
    status: str = "ready"  # ready, running, infected, error
    ble_address: Optional[str] = None
    last_seen: Optional[float] = None

class SimulationMetrics:
    """Tracks propagation metrics across the simulation"""
    
    def __init__(self):
        self.total_robots = 0
        self.infected_robots = 0
        self.infection_chain = []  # List of (source, target, timestamp)
        self.propagation_start = None
        self.propagation_complete = None
    
    def record_infection(self, source: str, target: str, timestamp: float):
        """Record an infection event"""
        self.infection_chain.append((source, target, timestamp))
        self.infected_robots += 1
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        return {
            "total_robots": self.total_robots,
            "infected_robots": self.infected_robots,
            "infection_rate": self.infected_robots / max(1, self.total_robots),
            "infection_count": len(self.infection_chain)
        }

class SimulatorCoordinator:
    """
    Central coordinator for distributed simulator network
    
    Manages simulators running across multiple physical devices
    (Raspberry Pis, laptops, etc.) and coordinates testing scenarios.
    """
    
    def __init__(self, c2_url: str, bind_port: int = None):
        """
        Initialize coordinator
        
        Args:
            c2_url: C2 server URL
            bind_port: Port for coordinator API (default: from config)
        """
        self.c2_url = c2_url
        self.bind_port = bind_port or config.SIMULATOR_COORDINATOR_PORT
        self.simulators: List[SimulatorNode] = []
        self.metrics = SimulationMetrics()
        
        print(f"[*] Simulator Coordinator initialized")
        print(f"    C2 Server: {c2_url}")
        print(f"    Bind Port: {self.bind_port}")
    
    async def register_simulator(self, host: str, port: int, robot_info: Dict):
        """
        Register a new simulator node
        
        Args:
            host: Simulator host address
            port: Simulator API port
            robot_info: Dict with model, serial, etc.
        """
        node = SimulatorNode(
            host=host,
            port=port,
            robot_id=robot_info.get("serial", "UNKNOWN"),
            model=robot_info.get("model", "Go2"),
            ble_address=robot_info.get("ble_address")
        )
        
        self.simulators.append(node)
        self.metrics.total_robots += 1
        
        print(f"[+] Registered simulator: {node.robot_id} @ {host}:{port}")
    
    async def rpc_call(self, node: SimulatorNode, method: str, params: Dict = None):
        """
        Make RPC call to simulator node
        
        Args:
            node: Target simulator node
            method: Method name (start, stop, infect, status)
            params: Method parameters
        """
        url = f"http://{node.host}:{node.port}/api/{method}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params or {}, timeout=10) as resp:
                    return await resp.json()
        except Exception as e:
            print(f"[!] RPC call failed to {node.robot_id}: {e}")
            node.status = "error"
            return None
    
    async def start_simulation(self, scenario: Dict = None):
        """
        Start simulation across all nodes
        
        Args:
            scenario: Simulation scenario parameters
        """
        print(f"\n[*] Starting distributed simulation...")
        print(f"    Nodes: {len(self.simulators)}")
        
        scenario = scenario or {
            "c2_url": self.c2_url,
            "auto_beacon": True
        }
        
        # Start all simulators
        tasks = []
        for node in self.simulators:
            task = self.rpc_call(node, "start", scenario)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful starts
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        print(f"[+] Started {success_count}/{len(self.simulators)} simulators")
    
    async def infect_patient_zero(self, target_serial: str):
        """
        Manually infect first robot to start propagation chain
        
        Args:
            target_serial: Serial number of robot to infect
        """
        target = self.find_simulator(target_serial)
        if not target:
            print(f"[!] Robot not found: {target_serial}")
            return False
        
        print(f"[!] Infecting patient zero: {target_serial}")
        
        result = await self.rpc_call(target, "force_infect")
        
        if result:
            print(f"[+] Infection started from {target_serial}")
            self.metrics.propagation_start = asyncio.get_event_loop().time()
            return True
        else:
            print(f"[!] Failed to infect {target_serial}")
            return False
    
    def find_simulator(self, robot_id: str) -> Optional[SimulatorNode]:
        """Find simulator by robot ID"""
        for node in self.simulators:
            if node.robot_id == robot_id:
                return node
        return None
    
    async def get_propagation_status(self) -> Dict:
        """
        Query all nodes for infection status
        
        Returns:
            Dict with propagation statistics
        """
        # Query each simulator
        tasks = []
        for node in self.simulators:
            task = self.rpc_call(node, "status")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count infected
        infected_count = 0
        for result in results:
            if result and isinstance(result, dict) and result.get("is_infected"):
                infected_count += 1
        
        self.metrics.infected_robots = infected_count
        
        return {
            "total": len(self.simulators),
            "infected": infected_count,
            "percentage": (infected_count / len(self.simulators) * 100) if self.simulators else 0,
            "metrics": self.metrics.get_summary()
        }
    
    async def get_propagation_graph(self) -> Dict:
        """
        Query C2 database for infection chain
        
        Returns:
            Graph data for visualization
        """
        # Query C2 for beacon/infection data
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.c2_url}/api/v1/devices"
                async with session.get(url) as resp:
                    devices = await resp.json()
            
            # Build graph
            nodes = []
            links = []
            
            for device in devices:
                if device["robot_id"].startswith(config.SIMULATOR_ID_PREFIX):
                    nodes.append({
                        "id": device["robot_id"],
                        "type": "simulator",
                        "infected": device.get("is_infected", False)
                    })
                    
                    if device.get("infected_by"):
                        links.append({
                            "source": device["infected_by"],
                            "target": device["robot_id"]
                        })
            
            return {"nodes": nodes, "links": links}
            
        except Exception as e:
            print(f"[!] Failed to get propagation graph: {e}")
            return {"nodes": [], "links": []}
    
    async def monitor_loop(self, interval: int = 10):
        """
        Monitor simulation progress
        
        Args:
            interval: Status check interval in seconds
        """
        print("\n[*] Starting monitoring loop (Ctrl+C to stop)...")
        
        try:
            while True:
                status = await self.get_propagation_status()
                
                print(f"\r[*] Infection Status: {status['infected']}/{status['total']} ({status['percentage']:.1f}%)", end="")
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n[*] Monitoring stopped")
    
    def list_simulators(self):
        """Print list of all registered simulators"""
        print("\nRegistered Simulators:")
        print("-" * 60)
        for node in self.simulators:
            print(f"  {node.robot_id:15s} @ {node.host:15s}:{node.port}  [{node.status}]")
        print("-" * 60)

async def deploy_to_device(host: str, port: int, model: str, serial: str):
    """
    Deploy simulator to a remote device
    
    This is a simplified version. Real deployment would use SSH/SCP
    to copy files and start the simulator service.
    
    Args:
        host: Target device IP
        port: SSH port
        model: Robot model
        serial: Serial number
    """
    print(f"[*] Deploying simulator to {host}...")
    print(f"    Model: {model}, Serial: {serial}")
    
    # In production, this would:
    # 1. SSH to device
    # 2. Copy simulator files
    # 3. Install dependencies
    # 4. Start simulator service
    
    # For now, just print instructions
    print(f"""
    Manual deployment steps for {host}:
    
    1. Copy files to device:
       scp robot_simulator.py command_sandbox.py requirements.txt pi@{host}:~/uniroam/
    
    2. SSH to device:
       ssh pi@{host}
    
    3. Install dependencies:
       cd ~/uniroam
       pip3 install -r requirements.txt
    
    4. Start simulator:
       python3 robot_simulator.py --serial {serial} --model {model} --mode distributed
    """)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Distributed Simulator Coordinator")
    parser.add_argument("--c2-url", required=True, help="C2 server URL")
    parser.add_argument("--port", type=int, default=config.SIMULATOR_COORDINATOR_PORT,
                       help="Coordinator API port")
    parser.add_argument("--config", help="Simulator config file (JSON)")
    
    args = parser.parse_args()
    
    async def main():
        coordinator = SimulatorCoordinator(args.c2_url, args.port)
        
        # Load simulator configuration
        if args.config:
            with open(args.config) as f:
                sim_config = json.load(f)
            
            # Register simulators from config
            for sim in sim_config.get("simulators", []):
                await coordinator.register_simulator(
                    host=sim["host"],
                    port=sim["port"],
                    robot_info=sim
                )
        
        # List simulators
        coordinator.list_simulators()
        
        # Start monitoring
        await coordinator.monitor_loop()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Coordinator stopped")

