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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse


class VirtualBoxBackup:
    """Main class for handling VirtualBox VM backups."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the backup manager with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.backup_dir = Path(self.config.get("backup_directory", "./backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        default_config = {
            "backup_directory": "./backups",
            "retention_days": 30,
            "vms_to_backup": [],  # Empty means all VMs
            "vms_to_exclude": [],
            "compression": True,
            "include_manifest": True,  # Generate manifest file with SHA-1 checksums for integrity verification
            "handle_running_vms": "pause",  # Options: "pause", "suspend", "skip", "fail"
            "log_file": "backup.log",
            "vboxmanage_path": "VBoxManage"
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logging.info(f"Loaded configuration from {config_path}")
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing config file: {e}")
                logging.info("Using default configuration")
        else:
            logging.warning(f"Config file {config_path} not found. Using defaults.")
            logging.info("Creating default config file...")
            self._create_default_config(config_path, default_config)
        
        return default_config
    
    def _create_default_config(self, config_path: str, config: Dict):
        """Create a default configuration file."""
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info(f"Created default config file at {config_path}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = self.config.get("log_file", "backup.log")
        log_level = self.config.get("log_level", "INFO").upper()
        
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _run_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def list_vms(self) -> List[Dict[str, str]]:
        """List all available VirtualBox VMs."""
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
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
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
        success, output = self._run_command([vboxmanage, "showvminfo", vm_uuid, "--machinereadable"])
        
        if not success:
            return "unknown"
        
        # Parse machine-readable output for VMState
        for line in output.split('\n'):
            if line.startswith('VMState='):
                state = line.split('=')[1].strip('"')
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
    
    def _pause_vm(self, vm_uuid: str, vm_name: str) -> bool:
        """Pause a running VM."""
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
        logging.info(f"Pausing VM {vm_name}...")
        success, output = self._run_command([vboxmanage, "controlvm", vm_uuid, "pause"])
        if success:
            logging.info(f"VM {vm_name} paused successfully")
        else:
            logging.error(f"Failed to pause VM {vm_name}: {output}")
        return success
    
    def _resume_vm(self, vm_uuid: str, vm_name: str) -> bool:
        """Resume a paused VM."""
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
        logging.info(f"Resuming VM {vm_name}...")
        success, output = self._run_command([vboxmanage, "controlvm", vm_uuid, "resume"])
        if success:
            logging.info(f"VM {vm_name} resumed successfully")
        else:
            logging.error(f"Failed to resume VM {vm_name}: {output}")
        return success
    
    def _suspend_vm(self, vm_uuid: str, vm_name: str) -> bool:
        """Suspend (save state) a running VM."""
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
        logging.info(f"Suspending VM {vm_name}...")
        success, output = self._run_command([vboxmanage, "controlvm", vm_uuid, "savestate"])
        if success:
            logging.info(f"VM {vm_name} suspended successfully")
        else:
            logging.error(f"Failed to suspend VM {vm_name}: {output}")
        return success
    
    def backup_vm(self, vm: Dict[str, str]) -> bool:
        """Backup a single VM."""
        vm_name = vm["name"]
        vm_uuid = vm["uuid"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{vm_name}_{timestamp}.ova"
        backup_path = self.backup_dir / backup_filename
        
        logging.info(f"Starting backup of VM: {vm_name}")
        
        vboxmanage = self.config.get("vboxmanage_path", "VBoxManage")
        
        # Get VM state
        vm_state = self._get_vm_state(vm_uuid)
        was_paused = False
        handle_running = self.config.get("handle_running_vms", "pause")
        
        # Handle running VMs based on configuration
        if vm_state == "running":
            if handle_running == "pause":
                if not self._pause_vm(vm_uuid, vm_name):
                    logging.error(f"Cannot backup {vm_name}: failed to pause VM")
                    return False
                was_paused = True
            elif handle_running == "suspend":
                if not self._suspend_vm(vm_uuid, vm_name):
                    logging.error(f"Cannot backup {vm_name}: failed to suspend VM")
                    return False
                # Note: Suspended VMs need to be started after backup, but we'll leave them suspended
                # as that's typically what users want when suspending
            elif handle_running == "skip":
                logging.warning(f"Skipping {vm_name}: VM is running and handle_running_vms is set to 'skip'")
                return False
            elif handle_running == "fail":
                logging.error(f"Cannot backup {vm_name}: VM is running and handle_running_vms is set to 'fail'")
                return False
            else:
                logging.warning(f"VM {vm_name} is running. Attempting backup anyway (may fail if disk is locked)...")
        
        # Export the VM
        export_command = [
            vboxmanage,
            "export",
            vm_uuid,
            "--output", str(backup_path)
        ]
        
        # Add manifest option if enabled (default: True)
        # Manifest file contains SHA-1 checksums for integrity verification
        if self.config.get("include_manifest", True):
            export_command.append("--manifest")
            logging.info(f"Exporting VM {vm_name} to {backup_path} with manifest (integrity checksums)")
        else:
            logging.info(f"Exporting VM {vm_name} to {backup_path}")
        
        success, output = self._run_command(export_command)
        
        # Resume VM if it was paused
        if was_paused:
            self._resume_vm(vm_uuid, vm_name)
        
        if not success:
            logging.error(f"Failed to export VM {vm_name}: {output}")
            return False
        
        logging.info(f"Successfully backed up {vm_name} to {backup_path}")
        
        # Compress if enabled
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
                    logging.info(f"Including manifest file: {manifest_path.name}")
            
            # Remove original files after successful compression
            backup_path.unlink()
            manifest_path = backup_path.with_suffix('.mf')
            if manifest_path.exists():
                manifest_path.unlink()
            logging.info(f"Compression complete. Removed original file(s).")
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
    
    args = parser.parse_args()
    
    backup_manager = VirtualBoxBackup(args.config)
    
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

