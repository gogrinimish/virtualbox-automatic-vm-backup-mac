#!/usr/bin/env python3
"""
VirtualBox Automatic VM Backup Script

This script automatically backs up VirtualBox VMs and manages old backups
with configurable retention policies.

Author: Open Source Community
License: MIT
"""

import os
import sys
import json
import subprocess
import tarfile
import logging
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse


class VirtualBoxBackup:
    """Main class for handling VirtualBox VM backups."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the backup manager with configuration."""
        # Get script directory to resolve relative paths
        self.script_dir = Path(__file__).parent.resolve()
        
        # Resolve config path relative to script directory if it's relative
        if not os.path.isabs(config_path):
            config_path = str(self.script_dir / config_path)
        
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Validate required config keys
        required_keys = ["backup_directory", "handle_running_vms", "vboxmanage_path"]
        for key in required_keys:
            if key not in self.config:
                error_msg = f"Required config key '{key}' is missing from config file"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                sys.exit(1)
        
        # Validate vboxmanage_path exists and is executable
        vboxmanage_path = self.config["vboxmanage_path"]
        if not os.path.isabs(vboxmanage_path):
            # If relative path, check if it's in PATH
            full_path = shutil.which(vboxmanage_path)
            if not full_path:
                # Check common locations for VBoxManage (launchd doesn't have full PATH)
                common_paths = [
                    "/usr/local/bin/VBoxManage",
                    "/Applications/VirtualBox.app/Contents/MacOS/VBoxManage",
                    "/opt/homebrew/bin/VBoxManage"
                ]
                found_path = None
                for common_path in common_paths:
                    if os.path.exists(common_path) and os.access(common_path, os.X_OK):
                        found_path = common_path
                        break
                
                if found_path:
                    error_msg = f"VBoxManage not found in PATH, but found at: {found_path}"
                    print(f"WARNING: {error_msg}", file=sys.stderr)
                    print(f"Please set 'vboxmanage_path' in config.json to: '{found_path}'", file=sys.stderr)
                    print(f"Note: launchd doesn't inherit your shell PATH, so use absolute paths.", file=sys.stderr)
                    sys.exit(1)
                else:
                    error_msg = f"VBoxManage not found: '{vboxmanage_path}' is not in PATH"
                    print(f"ERROR: {error_msg}", file=sys.stderr)
                    print(f"Please set 'vboxmanage_path' in config.json to the full path, e.g., '/usr/local/bin/VBoxManage' or '/Applications/VirtualBox.app/Contents/MacOS/VBoxManage'", file=sys.stderr)
                    sys.exit(1)
        else:
            # If absolute path, check if file exists and is executable
            if not os.path.exists(vboxmanage_path):
                error_msg = f"VBoxManage not found: '{vboxmanage_path}' does not exist"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                sys.exit(1)
            if not os.access(vboxmanage_path, os.X_OK):
                error_msg = f"VBoxManage not executable: '{vboxmanage_path}' is not executable"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                sys.exit(1)
        
        # Convert backup directory to absolute path
        backup_dir = self.config["backup_directory"]
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Backup directory: {self.backup_dir}")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file. Config file is required."""
        if not os.path.exists(config_path):
            error_msg = f"Config file does not exist: {config_path}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            print(f"Please create a config file (e.g., copy config.json.example to {config_path})", file=sys.stderr)
            sys.exit(1)
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logging.info(f"Loaded configuration from {config_path}")
            return config
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing config file {config_path}: {e}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error reading config file {config_path}: {e}"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        if "log_file" not in self.config:
            error_msg = "Required config key 'log_file' is missing from config file"
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
        log_file = self.config["log_file"]
        log_level = self.config.get("log_level", "INFO").upper()
        
        # Convert log file to absolute path (relative to script directory if relative)
        if os.path.isabs(log_file):
            log_file_path = Path(log_file)
        else:
            log_file_path = self.script_dir / log_file
        log_file_path = log_file_path.resolve()
        
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # Force reconfiguration if logging was already set up
        )
        logging.info(f"Logging to: {log_file_path}")
    
    def _run_command(self, command: List[str], show_progress: bool = False) -> Tuple[bool, str]:
        """Run a shell command and return success status and output.
        
        Args:
            command: Command to run
            show_progress: If True, show real-time output for long-running commands
        """
        try:
            if show_progress:
                # For long-running commands, show progress in real-time
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                output_lines = []
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        print(line, flush=True)  # Show progress in real-time
                        logging.info(line)  # Also log it
                        output_lines.append(line)
                
                process.wait()
                output = '\n'.join(output_lines)
                return process.returncode == 0, output
            else:
                # For quick commands, capture output normally
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False
                )
                return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Command execution error: {error_msg}")
            return False, error_msg
    
    def list_vms(self) -> List[Dict[str, str]]:
        """List all available VirtualBox VMs."""
        vboxmanage = self.config["vboxmanage_path"]
        success, output = self._run_command([vboxmanage, "list", "vms"])
        
        if not success:
            logging.error(f"Failed to list VMs: {output}")
            return []
        
        vms = []
        for line in output.strip().split('\n'):
            if line.strip():
                # Format: "vm_name" {uuid}
                parts = line.split('"')
                if len(parts) >= 2:
                    vm_name = parts[1]
                    uuid = parts[-1].strip().strip('{}')
                    vms.append({"name": vm_name, "uuid": uuid})
        
        return vms
    
    def get_vms_to_backup(self) -> List[Dict[str, str]]:
        """Get list of VMs that should be backed up based on configuration."""
        all_vms = self.list_vms()
        
        if not all_vms:
            logging.warning("No VMs found")
            return []
        
        vms_to_backup = self.config.get("vms_to_backup", [])
        vms_to_exclude = self.config.get("vms_to_exclude", [])
        
        if vms_to_backup:
            # Only backup specified VMs
            filtered = [vm for vm in all_vms if vm["name"] in vms_to_backup]
        else:
            # Backup all VMs except excluded ones
            filtered = [vm for vm in all_vms if vm["name"] not in vms_to_exclude]
        
        return filtered
    
    def _get_vm_state(self, vm_uuid: str) -> str:
        """Get the current state of a VM (running, paused, saved, poweredoff, etc.)."""
        vboxmanage = self.config["vboxmanage_path"]
        success, output = self._run_command([vboxmanage, "showvminfo", vm_uuid, "--machinereadable"])
        
        if not success:
            logging.warning(f"Could not get VM state, output: {output}")
            return "unknown"
        
        # Parse machine-readable output for VMState
        for line in output.split('\n'):
            if line.startswith('VMState='):
                state = line.split('=')[1].strip('"')
                logging.debug(f"VM state detected: {state}")
                return state
        
        # Fallback to parsing human-readable output
        if "running" in output.lower():
            return "running"
        elif "paused" in output.lower():
            return "paused"
        elif "saved" in output.lower():
            return "saved"
        else:
            return "poweredoff"
    
    def _suspend_vm(self, vm_uuid: str, vm_name: str) -> bool:
        """Suspend (save state) a running VM."""
        vboxmanage = self.config["vboxmanage_path"]
        logging.info(f"Suspending VM {vm_name}...")
        success, output = self._run_command([vboxmanage, "controlvm", vm_uuid, "savestate"])
        if success:
            logging.info(f"VM {vm_name} suspended successfully")
        else:
            logging.error(f"Failed to suspend VM {vm_name}: {output}")
        return success
    
    def _resume_vm(self, vm_uuid: str, vm_name: str) -> bool:
        """Resume/start a VM from saved or paused state."""
        vboxmanage = self.config["vboxmanage_path"]
        
        # Check current VM state to determine the correct command
        vm_state = self._get_vm_state(vm_uuid)
        
        if vm_state == "saved":
            # VM was saved (suspended), need to start it to restore from saved state
            logging.info(f"Starting VM {vm_name} from saved state...")
            success, output = self._run_command([vboxmanage, "startvm", vm_uuid, "--type", "headless"])
            if success:
                logging.info(f"VM {vm_name} started successfully from saved state")
            else:
                logging.error(f"Failed to start VM {vm_name} from saved state: {output}")
            return success
        elif vm_state == "paused":
            # VM is paused, use resume command
            logging.info(f"Resuming paused VM {vm_name}...")
            success, output = self._run_command([vboxmanage, "controlvm", vm_uuid, "resume"])
            if success:
                logging.info(f"VM {vm_name} resumed successfully")
            else:
                logging.error(f"Failed to resume VM {vm_name}: {output}")
            return success
        elif vm_state == "running":
            # VM is already running, nothing to do
            logging.info(f"VM {vm_name} is already running")
            return True
        else:
            logging.warning(f"VM {vm_name} is in state '{vm_state}', cannot resume/start")
            return False
    
    def backup_vm(self, vm: Dict[str, str]) -> bool:
        """Backup a single VM."""
        vm_name = vm["name"]
        vm_uuid = vm["uuid"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{vm_name}_{timestamp}.ova"
        backup_path = self.backup_dir / backup_filename
        
        logging.info(f"Starting backup of VM: {vm_name}")
        
        vboxmanage = self.config["vboxmanage_path"]
        
        # Get VM state
        vm_state = self._get_vm_state(vm_uuid)
        logging.info(f"VM {vm_name} current state: {vm_state}")
        handle_running = self.config["handle_running_vms"]
        
        # Track if VM was originally running (to resume after backup)
        was_running = False
        
        # Handle running VMs based on configuration
        if vm_state == "running":
            logging.info(f"VM {vm_name} is running, handling according to 'handle_running_vms' setting: {handle_running}")
            if handle_running == "suspend":
                was_running = True  # Mark that we need to resume after backup
                if not self._suspend_vm(vm_uuid, vm_name):
                    logging.error(f"Cannot backup {vm_name}: failed to suspend VM")
                    return False
                # Wait for suspend (savestate) to complete and release disk locks
                logging.info("Waiting for VM state to be saved and disk locks released...")
                time.sleep(5)
                # Verify VM is suspended
                new_state = self._get_vm_state(vm_uuid)
                if new_state != "saved":
                    logging.warning(f"VM state after suspend is '{new_state}' (expected 'saved'), but proceeding...")
            elif handle_running == "skip":
                logging.warning(f"Skipping {vm_name}: VM is running and handle_running_vms is set to 'skip'")
                return False
            elif handle_running == "fail":
                logging.error(f"Cannot backup {vm_name}: VM is running and handle_running_vms is set to 'fail'")
                return False
            else:
                logging.warning(f"VM {vm_name} is running. Attempting backup anyway (may fail if disk is locked)...")
        elif vm_state not in ["poweredoff", "saved", "paused", "aborted"]:
            logging.warning(f"VM {vm_name} is in state '{vm_state}' which may have disk locks. Proceeding with backup...")
        
        # Export the VM - use absolute path to ensure backup goes to the right location
        export_command = [
            vboxmanage,
            "export",
            vm_uuid,
            "--output", str(backup_path.resolve())
        ]
        
        # Add manifest option if enabled (default: True)
        # Manifest file contains SHA-1 checksums for integrity verification
        manifest_enabled = self.config.get("include_manifest", True)
        if manifest_enabled:
            export_command.append("--manifest")
            logging.info(f"Exporting VM {vm_name} to {backup_path} with manifest (integrity checksums)")
            manifest_path = backup_path.with_suffix('.mf')
            if self.config.get("compression", True):
                logging.info(f"Manifest file will be created as {manifest_path.name} and included in compressed archive")
            else:
                logging.info(f"Manifest file will be created as {manifest_path.name} alongside the OVA file")
        else:
            logging.info(f"Exporting VM {vm_name} to {backup_path}")
        
        logging.info("Starting export (this may take a while for large VMs)...")
        logging.info(f"Backup will be saved to: {backup_path.resolve()}")
        # Flush logs to ensure they're written
        logging.getLogger().handlers[0].flush() if logging.getLogger().handlers else None
        success, output = self._run_command(export_command, show_progress=True)
        
        if not success:
            logging.error(f"Failed to export VM {vm_name}: {output}")
            return False
        
        logging.info(f"Successfully backed up {vm_name} to {backup_path}")
        
        # Resume VM if it was running before backup (do this before compression)
        if was_running and self.config.get("resume_after_backup", True):
            logging.info(f"Resuming VM {vm_name} (was running before backup)...")
            if not self._resume_vm(vm_uuid, vm_name):
                logging.warning(f"Backup completed successfully, but failed to resume VM {vm_name}")
                # Don't fail the backup if resume fails - backup was successful
            else:
                logging.info(f"VM {vm_name} resumed successfully after backup")
        
        # Compress if enabled (after VM is resumed)
        if self.config.get("compression", True):
            self._compress_backup(backup_path)
        
        return True
    
    def _compress_backup(self, backup_path: Path):
        """Compress a backup file using tar.gz, including manifest file if present."""
        if not backup_path.exists():
            return
        
        compressed_path = backup_path.with_suffix('.tar.gz')
        logging.info(f"Compressing {backup_path} to {compressed_path}")
        
        try:
            # Create a tar.gz archive
            with tarfile.open(compressed_path, 'w:gz') as tar:
                # Add the OVA file
                tar.add(backup_path, arcname=backup_path.name)
                
                # If manifest file exists (when --manifest option was used), include it
                manifest_path = backup_path.with_suffix('.mf')
                if manifest_path.exists():
                    tar.add(manifest_path, arcname=manifest_path.name)
                    logging.info(f"Including manifest file {manifest_path.name} in compressed archive")
                else:
                    logging.info("No manifest file found (manifest may be disabled in config)")
            
            # Remove original files after successful compression
            backup_path.unlink()
            manifest_path = backup_path.with_suffix('.mf')
            if manifest_path.exists():
                manifest_path.unlink()
            logging.info(f"Compression complete. Original files removed. Manifest is included in {compressed_path.name}")
        except Exception as e:
            logging.error(f"Failed to compress backup: {e}")
            # Keep original file if compression fails
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        retention_days = self.config.get("retention_days", 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        logging.info(f"Cleaning up backups older than {retention_days} days (before {cutoff_date.strftime('%Y-%m-%d')})")
        
        deleted_count = 0
        freed_space = 0
        
        for backup_file in self.backup_dir.iterdir():
            if not backup_file.is_file():
                continue
            
            # Skip non-backup files (include .mf files for cleanup)
            if not (backup_file.suffix in ['.ova', '.tar.gz', '.mf'] or 
                    backup_file.name.endswith('.ova') or 
                    backup_file.name.endswith('.tar.gz') or
                    backup_file.name.endswith('.mf')):
                continue
            
            # Get file modification time
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if file_mtime < cutoff_date:
                file_size = backup_file.stat().st_size
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    freed_space += file_size
                    logging.info(f"Deleted old backup: {backup_file.name} ({file_size / (1024**3):.2f} GB)")
                except Exception as e:
                    logging.error(f"Failed to delete {backup_file.name}: {e}")
        
        if deleted_count > 0:
            logging.info(f"Cleanup complete: Deleted {deleted_count} backup(s), freed {freed_space / (1024**3):.2f} GB")
        else:
            logging.info("No old backups to clean up")
    
    def run_backup(self):
        """Run the complete backup process."""
        logging.info("=" * 60)
        logging.info("Starting VirtualBox VM Backup Process")
        logging.info("=" * 60)
        
        vms = self.get_vms_to_backup()
        
        if not vms:
            logging.warning("No VMs to backup")
            return
        
        logging.info(f"Found {len(vms)} VM(s) to backup")
        
        successful = 0
        failed = 0
        
        for vm in vms:
            if self.backup_vm(vm):
                successful += 1
            else:
                failed += 1
        
        logging.info(f"Backup process complete: {successful} successful, {failed} failed")
        
        # Run cleanup
        if self.config.get("auto_cleanup", True):
            self.cleanup_old_backups()
        
        logging.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VirtualBox Automatic VM Backup Script"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--list-vms",
        action="store_true",
        help="List all available VMs and exit"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only run cleanup, skip backup"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and check VBoxManage access, then exit"
    )
    
    args = parser.parse_args()
    
    backup_manager = VirtualBoxBackup(args.config)
    
    if args.validate:
        print("Validating configuration...")
        print(f"✓ Config file loaded: {args.config}")
        print(f"✓ Required config keys present")
        print(f"✓ VBoxManage path validated: {backup_manager.config['vboxmanage_path']}")
        
        # Test VBoxManage access
        print("\nTesting VBoxManage access...")
        vms = backup_manager.list_vms()
        if vms:
            print(f"✓ Successfully connected to VirtualBox")
            print(f"✓ Found {len(vms)} VM(s)")
            print("\nAvailable VMs:")
            for vm in vms:
                print(f"  - {vm['name']} ({vm['uuid']})")
        else:
            print("⚠ No VMs found (this may be normal if you have no VMs)")
        
        print(f"\n✓ Backup directory: {backup_manager.backup_dir}")
        print(f"✓ Log file: {backup_manager.config['log_file']}")
        print("\n✓ Configuration validation passed!")
        return
    
    if args.list_vms:
        vms = backup_manager.list_vms()
        print("\nAvailable VirtualBox VMs:")
        print("-" * 60)
        for vm in vms:
            print(f"  Name: {vm['name']}")
            print(f"  UUID: {vm['uuid']}")
            print()
        return
    
    if args.cleanup_only:
        backup_manager.cleanup_old_backups()
        return
    
    backup_manager.run_backup()


if __name__ == "__main__":
    main()

