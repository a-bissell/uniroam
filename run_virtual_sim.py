#!/usr/bin/env python3
"""
Virtual Robot Simulator Launcher
Launch multiple simulated robots on a single machine
"""

import asyncio
import os
import sys
import random
import argparse
from typing import List

# Enable virtual BLE mode
os.environ["VIRTUAL_BLE"] = "true"

import virtual_ble
from robot_simulator import UnitreeSimulator
from uniroam import config

class VirtualSimulatorSwarm:
    """
    Manages a swarm of virtual robot simulators
    """
    
    def __init__(self, count: int = 5, c2_url: str = None):
        """
        Initialize simulator swarm
        
        Args:
            count: Number of robots to simulate
            c2_url: C2 server URL (uses config default if None)
        """
        self.count = count
        self.c2_url = c2_url or config.get_c2_url()
        self.simulators: List[UnitreeSimulator] = []
        self.adapter = virtual_ble.get_virtual_adapter()
        
        print(f"\n{'='*60}")
        print(f"UniRoam Virtual Simulator Swarm")
        print(f"{'='*60}")
        print(f"Simulators: {count}")
        print(f"C2 Server:  {self.c2_url}")
        print(f"Mode:       Virtual BLE (no hardware required)")
        print(f"{'='*60}\n")
    
    async def create_simulators(self):
        """Create and initialize all simulators"""
        models = ["Go2", "G1", "B2", "H1"]
        
        for i in range(self.count):
            model = random.choice(models)
            serial = f"SIM_{i:03d}"
            
            simulator = UnitreeSimulator(
                model=model,
                serial=serial,
                mode="virtual"
            )
            
            # Attach to virtual BLE adapter
            simulator.attach_ble(self.adapter)
            
            self.simulators.append(simulator)
            
            # Small delay to stagger startup
            await asyncio.sleep(0.1)
        
        print(f"\n[+] Created {len(self.simulators)} virtual robots")
        self._print_robot_list()
    
    def _print_robot_list(self):
        """Print list of all simulated robots"""
        print("\nSimulated Robots:")
        print("-" * 60)
        for sim in self.simulators:
            print(f"  {sim.device_name:20s} @ {sim.ble_device.address}")
        print("-" * 60 + "\n")
    
    async def force_infect(self, serial: str):
        """
        Manually infect a specific robot
        
        Args:
            serial: Serial number or device name of robot to infect
        """
        # Normalize input (case-insensitive matching)
        serial_lower = serial.lower()
        
        for sim in self.simulators:
            # Check both serial and full device name
            if (sim.serial.lower() == serial_lower or 
                sim.device_name.lower() == serial_lower):
                print(f"[!] Forcing infection of {sim.device_name}")
                await sim._handle_infection("MANUAL_INFECTION")
                return True
        
        # Provide helpful error message
        print(f"[!] Available robots:")
        for sim in self.simulators:
            print(f"    - {sim.device_name} (serial: {sim.serial})")
        return False
    
    async def run(self):
        """Run all simulators concurrently"""
        print("[*] Starting simulator swarm...")
        print("[*] Press Ctrl+C to stop\n")
        
        try:
            # Run all simulators
            tasks = [sim.run() for sim in self.simulators]
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            print("\n[*] Shutting down simulator swarm...")
            self.cleanup()
    
    def cleanup(self):
        """Clean up all simulators"""
        for sim in self.simulators:
            sim.cleanup()
        print("[+] All simulators stopped")
    
    def get_status(self):
        """Get status of all simulators"""
        return [sim.get_status() for sim in self.simulators]

async def interactive_mode(swarm: VirtualSimulatorSwarm):
    """
    Interactive mode with command prompt
    """
    print("\n" + "="*60)
    print("Interactive Mode - Available Commands:")
    print("="*60)
    print("  list           - List all simulators")
    print("  infect <id>    - Manually infect a robot (use serial or full name)")
    print("                   Examples: 'infect SIM_000' or 'infect Go2_SIM_SIM_000'")
    print("  status         - Show infection status")
    print("  help           - Show this help")
    print("  exit           - Exit interactive mode")
    print("="*60 + "\n")
    
    while True:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, 
                input,
                "simulator> "
            )
            
            cmd = cmd.strip().lower()
            
            if cmd == "exit":
                break
            elif cmd == "list":
                swarm._print_robot_list()
            elif cmd.startswith("infect "):
                serial = cmd.split()[1]
                if await swarm.force_infect(serial):
                    print(f"[+] Infected {serial}")
                else:
                    print(f"[!] Robot not found: {serial}")
            elif cmd == "status":
                statuses = swarm.get_status()
                infected = sum(1 for s in statuses if s["is_infected"])
                print(f"\nInfection Status: {infected}/{len(statuses)} infected")
                for status in statuses:
                    icon = "🦠" if status["is_infected"] else "✓"
                    print(f"  {icon} {status['device_name']}")
            elif cmd == "help":
                print("\nCommands:")
                print("  list           - List all simulators")
                print("  infect <id>    - Infect robot (e.g., 'infect SIM_000')")
                print("  status         - Show infection status")
                print("  exit           - Exit interactive mode")
            else:
                print(f"Unknown command: {cmd}")
                
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

async def main():
    parser = argparse.ArgumentParser(
        description="Virtual Robot Simulator - Test worm propagation without hardware"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=int(os.getenv("SIMULATOR_COUNT", "5")),
        help="Number of robots to simulate (default: 5)"
    )
    parser.add_argument(
        "--c2-url",
        default=None,
        help="C2 server URL (default: from config)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode with command prompt"
    )
    parser.add_argument(
        "--auto-infect",
        default=None,
        help="Automatically infect robot with given serial (e.g., SIM_000)"
    )
    
    args = parser.parse_args()
    
    # Create simulator swarm
    swarm = VirtualSimulatorSwarm(
        count=args.count,
        c2_url=args.c2_url
    )
    
    # Create all simulators
    await swarm.create_simulators()
    
    # Auto-infect if requested
    if args.auto_infect:
        print(f"[*] Auto-infecting {args.auto_infect} in 3 seconds...")
        await asyncio.sleep(3)
        await swarm.force_infect(args.auto_infect)
    
    # Start interactive mode or run normally
    if args.interactive:
        # Run swarm in background and interactive mode in foreground
        swarm_task = asyncio.create_task(swarm.run())
        try:
            await interactive_mode(swarm)
        finally:
            swarm_task.cancel()
            swarm.cleanup()
    else:
        # Just run the swarm
        await swarm.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Simulator terminated")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

