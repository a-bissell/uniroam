#!/usr/bin/env python3
"""
Virtual BLE Backend for Robot Simulation
Emulates BLE communication without hardware adapters
"""

import asyncio
import random
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from uniroam import config

# Global virtual adapter instance
_virtual_adapter = None

def get_virtual_adapter():
    """Get or create the global virtual BLE adapter"""
    global _virtual_adapter
    if _virtual_adapter is None:
        _virtual_adapter = VirtualBLEAdapter()
    return _virtual_adapter

@dataclass
class BLEAdvertisement:
    """BLE advertisement data"""
    name: str
    address: str
    rssi: int
    service_uuids: List[str]
    manufacturer_data: Dict = None

class VirtualBLEDevice:
    """
    Virtual BLE device representation
    Emulates a Unitree robot's BLE interface
    """
    
    def __init__(self, name: str, address: str, simulator=None):
        self.name = name
        self.address = address
        self.simulator = simulator  # Reference to robot simulator
        
        # Characteristics storage
        self.characteristics = {
            config.NOTIFY_CHAR_UUID: bytearray(),
            config.WRITE_CHAR_UUID: bytearray(),
            config.DEVICE_NAME_UUID: name.encode()
        }
        
        # Notification callbacks
        self.notification_callbacks = []
        self.connected = False
        self.rssi = random.randint(-70, -40)  # Simulated signal strength
    
    async def write_characteristic(self, uuid: str, data: bytes):
        """
        Write data to characteristic
        Forwards to simulator for processing
        """
        self.characteristics[uuid] = bytearray(data)
        
        # If this is the write characteristic, process the command
        if uuid == config.WRITE_CHAR_UUID and self.simulator:
            response = await self.simulator.handle_ble_write(data)
            
            # Send response via notification
            if response:
                await self.trigger_notification(config.NOTIFY_CHAR_UUID, response)
    
    async def read_characteristic(self, uuid: str) -> bytes:
        """Read data from characteristic"""
        return bytes(self.characteristics.get(uuid, bytearray()))
    
    async def trigger_notification(self, uuid: str, data: bytes):
        """Trigger notification to all registered callbacks"""
        for callback in self.notification_callbacks:
            try:
                await callback(uuid, data)
            except Exception as e:
                print(f"[!] Notification callback error: {e}")
    
    def start_notify(self, uuid: str, callback: Callable):
        """Register notification callback"""
        self.notification_callbacks.append(callback)
    
    def stop_notify(self, uuid: str):
        """Clear notification callbacks"""
        self.notification_callbacks.clear()

class VirtualBLEConnection:
    """
    Virtual BLE connection
    Mimics BleakClient interface for compatibility
    """
    
    def __init__(self, device: VirtualBLEDevice):
        self.device = device
        self.is_connected = False
    
    async def connect(self):
        """Establish virtual connection"""
        self.is_connected = True
        self.device.connected = True
        await asyncio.sleep(0.1)  # Simulate connection delay
    
    async def disconnect(self):
        """Close virtual connection"""
        self.is_connected = False
        self.device.connected = False
    
    async def write_gatt_char(self, uuid: str, data: bytes):
        """Write to GATT characteristic"""
        if not self.is_connected:
            raise RuntimeError("Not connected")
        await self.device.write_characteristic(uuid, data)
    
    async def read_gatt_char(self, uuid: str) -> bytes:
        """Read from GATT characteristic"""
        if not self.is_connected:
            raise RuntimeError("Not connected")
        return await self.device.read_characteristic(uuid)
    
    async def start_notify(self, uuid: str, callback: Callable):
        """Start notifications"""
        if not self.is_connected:
            raise RuntimeError("Not connected")
        self.device.start_notify(uuid, callback)
    
    async def stop_notify(self, uuid: str):
        """Stop notifications"""
        self.device.stop_notify(uuid)

class VirtualBLEAdapter:
    """
    Virtual BLE adapter
    Manages multiple virtual devices and provides discovery
    """
    
    def __init__(self):
        self.devices: Dict[str, VirtualBLEDevice] = {}  # MAC -> Device
        self.scan_callbacks = []
        self._next_mac_id = 0
    
    def generate_mac_address(self) -> str:
        """Generate unique virtual MAC address"""
        mac = f"{config.VIRTUAL_BLE_MAC_PREFIX}:{self._next_mac_id:02X}:{random.randint(0, 255):02X}"
        self._next_mac_id += 1
        return mac
    
    def register_device(self, name: str, address: Optional[str] = None, simulator=None) -> VirtualBLEDevice:
        """
        Register a new virtual device
        
        Args:
            name: Device name (e.g., "Go2_SIM_001")
            address: MAC address (auto-generated if None)
            simulator: Robot simulator instance
            
        Returns:
            VirtualBLEDevice instance
        """
        if address is None:
            address = self.generate_mac_address()
        
        device = VirtualBLEDevice(name, address, simulator)
        self.devices[address] = device
        print(f"[+] Registered virtual device: {name} @ {address}")
        return device
    
    def unregister_device(self, address: str):
        """Remove a virtual device"""
        if address in self.devices:
            del self.devices[address]
    
    async def discover(self, timeout: float = 10.0, return_adv: bool = True) -> Dict:
        """
        Discover virtual devices
        Mimics BleakScanner.discover() interface
        
        Args:
            timeout: Discovery duration (ignored in virtual mode)
            return_adv: Return advertisement data
            
        Returns:
            Dict of {address: (device, adv)} if return_adv=True
        """
        await asyncio.sleep(0.1)  # Simulate scan delay
        
        results = {}
        for address, device in self.devices.items():
            adv = BLEAdvertisement(
                name=device.name,
                address=address,
                rssi=device.rssi,
                service_uuids=[config.UNITREE_SERVICE_UUID],
                manufacturer_data={}
            )
            
            # Create a pseudo-device object for compatibility
            class PseudoDevice:
                def __init__(self, name, addr):
                    self.name = name
                    self.address = addr
            
            pseudo_dev = PseudoDevice(device.name, address)
            results[address] = (pseudo_dev, adv)
        
        return results
    
    def get_device(self, address: str) -> Optional[VirtualBLEDevice]:
        """Get device by MAC address"""
        return self.devices.get(address)
    
    def create_client(self, address: str) -> VirtualBLEConnection:
        """
        Create virtual BLE client
        Mimics BleakClient interface
        
        Args:
            address: Device MAC address
            
        Returns:
            VirtualBLEConnection instance
        """
        device = self.devices.get(address)
        if device is None:
            raise ValueError(f"Device not found: {address}")
        
        return VirtualBLEConnection(device)
    
    def list_devices(self) -> List[Dict]:
        """Get list of all registered devices"""
        return [
            {
                "name": dev.name,
                "address": addr,
                "connected": dev.connected,
                "rssi": dev.rssi
            }
            for addr, dev in self.devices.items()
        ]


# Monkey-patching utilities for transparent Bleak integration

class VirtualBleakScanner:
    """
    Virtual scanner that mimics BleakScanner
    Used to transparently replace real BLE scanning
    """
    
    def __init__(self, *args, **kwargs):
        self.adapter = get_virtual_adapter()
    
    @staticmethod
    async def discover(timeout=10.0, return_adv=True, **kwargs):
        """Discover devices using virtual adapter"""
        adapter = get_virtual_adapter()
        return await adapter.discover(timeout, return_adv)

class VirtualBleakClient:
    """
    Virtual client that mimics BleakClient
    Used to transparently replace real BLE connections
    """
    
    def __init__(self, address_or_device, *args, **kwargs):
        if isinstance(address_or_device, str):
            self.address = address_or_device
        else:
            self.address = address_or_device.address
        
        self.adapter = get_virtual_adapter()
        self.connection = None
        self.timeout = kwargs.get('timeout', 30.0)
    
    async def connect(self):
        """Connect to virtual device"""
        self.connection = self.adapter.create_client(self.address)
        await self.connection.connect()
    
    async def disconnect(self):
        """Disconnect from virtual device"""
        if self.connection:
            await self.connection.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connection and self.connection.is_connected
    
    async def write_gatt_char(self, uuid, data):
        """Write to characteristic"""
        if isinstance(uuid, int):
            # Handle numeric handle (fallback mode)
            uuid = config.WRITE_CHAR_UUID
        return await self.connection.write_gatt_char(uuid, data)
    
    async def read_gatt_char(self, uuid):
        """Read from characteristic"""
        return await self.connection.read_gatt_char(uuid)
    
    async def start_notify(self, uuid, callback):
        """Start notifications"""
        if isinstance(uuid, int):
            # Handle numeric handle (fallback mode)
            uuid = config.NOTIFY_CHAR_UUID
        await self.connection.start_notify(uuid, callback)
    
    async def stop_notify(self, uuid):
        """Stop notifications"""
        await self.connection.stop_notify(uuid)

def enable_virtual_mode():
    """
    Enable virtual BLE mode by monkey-patching Bleak
    Call this before running any BLE code in virtual mode
    """
    import sys
    from types import ModuleType
    
    # Create fake bleak module
    bleak = ModuleType('bleak')
    bleak.BleakScanner = VirtualBleakScanner
    bleak.BleakClient = VirtualBleakClient
    sys.modules['bleak'] = bleak
    
    print("[*] Virtual BLE mode enabled")

if __name__ == "__main__":
    # Test the virtual BLE system
    print("[*] Testing Virtual BLE System")
    
    async def test():
        adapter = get_virtual_adapter()
        
        # Register some virtual devices
        adapter.register_device("Go2_SIM_001")
        adapter.register_device("Go2_SIM_002")
        adapter.register_device("B2_SIM_001")
        
        # Test discovery
        print("\n[+] Discovering devices:")
        devices = await adapter.discover()
        for addr, (dev, adv) in devices.items():
            print(f"    {dev.name} @ {addr} (RSSI: {adv.rssi})")
        
        # Test connection
        print("\n[+] Testing connection:")
        client = adapter.create_client(list(devices.keys())[0])
        await client.connect()
        print(f"    Connected: {client.is_connected}")
        await client.disconnect()
        print(f"    Disconnected: {not client.is_connected}")
        
        print("\n[+] Virtual BLE test complete")
    
    asyncio.run(test())

