#!/usr/bin/env python3
"""
Distributed Simulator Launcher
Deploy and coordinate simulators across multiple physical devices
"""

import asyncio
import json
import sys
from typing import List, Dict
from sim_coordinator import SimulatorCoordinator, deploy_to_device

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Distributed Robot Simulator - Deploy across Raspberry Pis and laptops"
    )
    parser.add_argument(
        "--c2-url",
        required=True,
        help="C2 server URL (e.g., http://192.168.1.100:8443)"
    )
    parser.add_argument(
        "--config",
        default="simulator_config.json",
        help="Configuration file with device list (default: simulator_config.json)"
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy simulators to devices (shows deployment instructions)"
    )
    parser.add_argument(
        "--patient-zero",
        default="SIM_000",
        help="Robot ID to infect first (default: SIM_000)"
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Don't start monitoring loop"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("UniRoam Distributed Simulator")
    print("="*60)
    print(f"C2 Server: {args.c2_url}")
    print(f"Config:    {args.config}")
    print("="*60 + "\n")
    
    # Load configuration
    try:
        with open(args.config) as f:
            sim_config = json.load(f)
    except FileNotFoundError:
        print(f"[!] Configuration file not found: {args.config}")
        print("\nCreating example configuration...")
        create_example_config(args.config)
        print(f"[+] Created {args.config}")
        print(f"[*] Edit this file and run again")
        return
    
    # Create coordinator
    coordinator = SimulatorCoordinator(args.c2_url)
    
    # Register simulators from config
    print("[*] Registering simulators...")
    for sim in sim_config.get("simulators", []):
        await coordinator.register_simulator(
            host=sim["host"],
            port=sim.get("port", 5555),
            robot_info={
                "serial": sim["serial"],
                "model": sim.get("model", "Go2"),
                "ble_address": sim.get("ble_address")
            }
        )
    
    coordinator.list_simulators()
    
    # Deploy if requested
    if args.deploy:
        print("\n[*] Deployment mode enabled")
        for sim in sim_config.get("simulators", []):
            await deploy_to_device(
                host=sim["host"],
                port=22,  # SSH port
                model=sim.get("model", "Go2"),
                serial=sim["serial"]
            )
        print("\n[*] Deployment instructions printed above")
        return
    
    # Start simulation
    print("\n[*] Starting distributed simulation...")
    await coordinator.start_simulation()
    
    # Wait a bit for simulators to initialize
    print("[*] Waiting for simulators to initialize...")
    await asyncio.sleep(5)
    
    # Infect patient zero
    print(f"\n[!] Infecting patient zero: {args.patient_zero}")
    await coordinator.infect_patient_zero(args.patient_zero)
    
    # Monitor propagation
    if not args.no_monitor:
        print("\n" + "="*60)
        print("Monitoring Propagation")
        print("="*60)
        await coordinator.monitor_loop(interval=5)

def create_example_config(filename: str):
    """Create example simulator configuration file"""
    config = {
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
        ],
        "scenario": {
            "patient_zero": "SIM_000",
            "propagation_rate_limit": 5,
            "beacon_interval": 120
        }
    }
    
    with open(filename, "w") as f:
        json.dump(config, f, indent=2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[*] Distributed simulation stopped")
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

