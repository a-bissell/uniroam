#!/usr/bin/env python3
"""
Command Sandbox for Safe Worm Execution
Provides isolated execution environment for testing
"""

import os
import sys
import subprocess
import tempfile
import shutil
from typing import Optional, Dict
from pathlib import Path
from uniroam import config

class SecurityError(Exception):
    """Raised when a dangerous command is blocked"""
    pass

class CommandSandbox:
    """
    Sandbox for executing worm commands safely
    
    Provides isolation using Docker containers (preferred) or
    subprocess with restricted permissions (fallback).
    """
    
    # Dangerous commands that should never be executed
    BLACKLIST = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero",
        "dd if=/dev/random",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sda",
        "mv / /dev/null",
        "wget http",  # Block external downloads for now
        "curl http",   # Block external downloads for now
    ]
    
    def __init__(self, root_path: str, allow_network: bool = True, robot_id: str = "UNKNOWN"):
        """
        Initialize sandbox environment
        
        Args:
            root_path: Root directory for sandbox filesystem
            allow_network: Whether to allow network access
            robot_id: Identifier for this sandbox instance
        """
        self.root_path = Path(root_path)
        self.allow_network = allow_network
        self.robot_id = robot_id
        self.sandbox_type = config.SANDBOX_TYPE
        
        # Create isolated filesystem
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        # Create basic directory structure
        (self.root_path / "home").mkdir(exist_ok=True)
        (self.root_path / "tmp").mkdir(exist_ok=True)
        (self.root_path / "var" / "log").mkdir(parents=True, exist_ok=True)
        (self.root_path / "etc").mkdir(exist_ok=True)
        
        # Execution log
        self.log_file = self.root_path / "sandbox.log"
        self.command_history = []
    
    def _is_dangerous(self, command: str) -> bool:
        """Check if command contains dangerous patterns"""
        cmd_lower = command.lower()
        for danger in self.BLACKLIST:
            if danger.lower() in cmd_lower:
                return True
        return False
    
    def _log_execution(self, command: str, result: str, exit_code: int):
        """Log command execution"""
        log_entry = f"[{self.robot_id}] CMD: {command} | EXIT: {exit_code}\n"
        self.command_history.append({
            "command": command,
            "exit_code": exit_code,
            "output": result[:500]  # Truncate long output
        })
        
        with open(self.log_file, "a") as f:
            f.write(log_entry)
    
    def execute(self, command: str, timeout: int = 30) -> Dict:
        """
        Execute command in sandbox
        
        Args:
            command: Shell command to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict with stdout, stderr, exit_code
            
        Raises:
            SecurityError: If command is dangerous
        """
        # Security check
        if self._is_dangerous(command):
            raise SecurityError(f"Blocked dangerous command: {command}")
        
        # Route to appropriate sandbox
        if self.sandbox_type == "docker":
            result = self._execute_docker(command, timeout)
        else:
            result = self._execute_subprocess(command, timeout)
        
        # Log execution
        self._log_execution(command, result["stdout"], result["exit_code"])
        
        return result
    
    def _execute_docker(self, command: str, timeout: int) -> Dict:
        """Execute in Docker container"""
        try:
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "host" if self.allow_network else "none",
                "-v", f"{self.root_path.absolute()}:/workspace",
                "-w", "/workspace",
                "--memory", "512m",  # Limit memory
                "--cpus", "1",  # Limit CPU
                config.SIMULATOR_DOCKER_IMAGE,
                "bash", "-c", command
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timeout",
                "exit_code": 124
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1
            }
    
    def _execute_subprocess(self, command: str, timeout: int) -> Dict:
        """Execute using subprocess (less isolated)"""
        try:
            # Create environment with restricted PATH
            env = os.environ.copy()
            env["HOME"] = str(self.root_path / "home")
            env["TMPDIR"] = str(self.root_path / "tmp")
            
            # Execute in sandbox directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root_path),
                capture_output=True,
                timeout=timeout,
                text=True,
                env=env
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timeout",
                "exit_code": 124
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1
            }
    
    def get_env(self) -> Dict[str, str]:
        """Get sandbox environment variables"""
        return {
            "HOME": str(self.root_path / "home"),
            "TMPDIR": str(self.root_path / "tmp"),
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "ROBOT_ID": self.robot_id,
            "SANDBOX": "1"
        }
    
    def cleanup(self):
        """Remove sandbox filesystem"""
        if self.root_path.exists():
            shutil.rmtree(self.root_path)
    
    def get_history(self):
        """Get command execution history"""
        return self.command_history

def create_sandbox(robot_id: str) -> CommandSandbox:
    """
    Factory function to create a sandbox
    
    Args:
        robot_id: Unique identifier for this robot
        
    Returns:
        Configured CommandSandbox instance
    """
    sandbox_path = f"/tmp/robot_sim_{robot_id}"
    return CommandSandbox(
        root_path=sandbox_path,
        allow_network=config.SANDBOX_ALLOW_NETWORK,
        robot_id=robot_id
    )

if __name__ == "__main__":
    # Test the sandbox
    print("[*] Testing CommandSandbox")
    
    sandbox = create_sandbox("TEST_001")
    
    # Test safe command
    print("\n[+] Testing safe command:")
    result = sandbox.execute("echo 'Hello from sandbox'")
    print(f"    Output: {result['stdout'].strip()}")
    
    # Test dangerous command
    print("\n[+] Testing dangerous command:")
    try:
        sandbox.execute("rm -rf /")
        print("    ERROR: Dangerous command was not blocked!")
    except SecurityError as e:
        print(f"    Blocked: {e}")
    
    # Cleanup
    sandbox.cleanup()
    print("\n[+] Sandbox test complete")

