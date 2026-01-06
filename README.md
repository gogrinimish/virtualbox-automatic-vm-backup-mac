# VirtualBox Automatic VM Backup for macOS

A Python script to automatically backup VirtualBox VMs on macOS with configurable retention policies and cleanup of old backups.

## Features

- 🔄 **Automatic VM Backup**: Export all or selected VirtualBox VMs to OVA format
- 🗜️ **Compression**: Optional compression of backups to save disk space
- 🧹 **Automatic Cleanup**: Remove old backups based on configurable retention period
- ⚙️ **Highly Configurable**: Customize backup location, retention, VM selection, and more
- 📝 **Comprehensive Logging**: Detailed logs for all backup operations
- 🎯 **Selective Backup**: Choose specific VMs to backup or exclude certain VMs

## Requirements

- macOS (tested on macOS 10.14+)
- Python 3.7 or higher
- VirtualBox installed with `VBoxManage` command available in PATH
- Sufficient disk space for backups

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/virtualbox-automatic-vm-backup-mac.git
cd virtualbox-automatic-vm-backup-mac
```

2. Copy the example configuration file:
```bash
cp config.json.example config.json
```

3. Edit `config.json` to customize settings (see Configuration section)

4. Make the script executable:
```bash
chmod +x vbox_backup.py
```

## Configuration

Edit `config.json` to customize the backup behavior:

```json
{
    "backup_directory": "./backups",
    "retention_days": 30,
    "vms_to_backup": [],
    "vms_to_exclude": [],
    "compression": true,
    "include_manifest": true,
    "handle_running_vms": "pause",
    "auto_cleanup": true,
    "log_file": "backup.log",
    "log_level": "INFO",
    "vboxmanage_path": "VBoxManage"
}
```

### Configuration Options

- **`backup_directory`**: Directory where backups will be stored (default: `./backups`)
- **`retention_days`**: Number of days to keep backups before automatic deletion (default: 30)
- **`vms_to_backup`**: List of VM names to backup. Empty array `[]` means backup all VMs
  - Example: `["MyVM", "TestVM"]` - only backup these VMs
- **`vms_to_exclude`**: List of VM names to exclude from backup
  - Example: `["TemporaryVM"]` - backup all VMs except this one
- **`compression`**: Enable/disable compression of backups (default: `true`)
- **`include_manifest`**: Generate manifest file (.mf) with SHA-1 checksums for integrity verification (default: `true`)
  - Recommended for backups to detect corruption during restore
  - Manifest file is included in compressed backups
- **`handle_running_vms`**: How to handle VMs that are running during backup (default: `"suspend"`)
  - `"suspend"`: Save VM state and suspend, then backup (recommended - releases disk locks, VM remains suspended after backup)
  - `"pause"`: Pause the VM, backup, then resume (may not release disk locks in all cases)
  - `"skip"`: Skip running VMs and log a warning
  - `"fail"`: Fail the backup if VM is running
- **`auto_cleanup`**: Automatically clean up old backups after backup (default: `true`)
- **`log_file`**: Path to log file (default: `backup.log`)
- **`log_level`**: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- **`vboxmanage_path`**: Path to VBoxManage command (default: `VBoxManage`)

### Configuration Examples

**Backup only specific VMs:**
```json
{
    "vms_to_backup": ["ProductionVM", "DevelopmentVM"],
    "vms_to_exclude": []
}
```

**Backup all VMs except certain ones:**
```json
{
    "vms_to_backup": [],
    "vms_to_exclude": ["TemporaryVM", "TestVM"]
}
```

**Long-term retention (90 days):**
```json
{
    "retention_days": 90,
    "backup_directory": "/Volumes/ExternalDrive/VMBackups"
}
```

## Usage

### Basic Backup

Run a backup with default settings:
```bash
python3 vbox_backup.py
```

Or using the executable:
```bash
./vbox_backup.py
```

### List Available VMs

See all VirtualBox VMs without running a backup:
```bash
python3 vbox_backup.py --list-vms
```

### Cleanup Only

Run cleanup of old backups without creating new backups:
```bash
python3 vbox_backup.py --cleanup-only
```

### Custom Configuration File

Use a different configuration file:
```bash
python3 vbox_backup.py --config /path/to/custom-config.json
```

## Automation

### Using cron (macOS)

To run backups automatically, add a cron job:

1. Open crontab:
```bash
crontab -e
```

2. Add a line to run backups daily at 2 AM:
```bash
0 2 * * * cd /path/to/virtualbox-automatic-vm-backup-mac && /usr/bin/python3 vbox_backup.py >> /path/to/backup.log 2>&1
```

3. For weekly backups (every Sunday at 2 AM):
```bash
0 2 * * 0 cd /path/to/virtualbox-automatic-vm-backup-mac && /usr/bin/python3 vbox_backup.py >> /path/to/backup.log 2>&1
```

### Using launchd (macOS - Recommended)

Create a plist file for launchd (more reliable than cron on macOS):

1. Create `~/Library/LaunchAgents/com.vboxbackup.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vboxbackup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/virtualbox-automatic-vm-backup-mac/vbox_backup.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/virtualbox-automatic-vm-backup-mac/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/virtualbox-automatic-vm-backup-mac/launchd.error.log</string>
</dict>
</plist>
```

2. Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.vboxbackup.plist
```

3. To unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.vboxbackup.plist
```

## Backup Format

Backups are created in OVA (Open Virtualization Format Archive) format, which is:
- Portable across different virtualization platforms
- Self-contained (includes VM configuration and disk images)
- Can be imported into VirtualBox or other virtualization software

When the `include_manifest` option is enabled (default), a manifest file (`.mf`) is also created containing SHA-1 checksums of all files in the export. This allows VirtualBox to verify the integrity of the backup during import, detecting any corruption or tampering.

When compression is enabled, backups are stored as `.tar.gz` files, which include both the OVA file and the manifest file (if manifest is enabled).

## Restoring Backups

To restore a backup:

1. **From OVA file:**
```bash
VBoxManage import /path/to/backup/VMName_20240101_120000.ova
```

2. **From compressed backup:**
```bash
# First extract
tar -xzf VMName_20240101_120000.tar.gz

# Then import the OVA
VBoxManage import VMName_20240101_120000.ova
```

## Troubleshooting

### VBoxManage not found

If you get an error that `VBoxManage` is not found:

1. Check if VirtualBox is installed:
```bash
which VBoxManage
```

2. If not in PATH, add VirtualBox to your PATH or specify the full path in `config.json`:
```json
{
    "vboxmanage_path": "/Applications/VirtualBox.app/Contents/MacOS/VBoxManage"
}
```

### Permission Errors

If you encounter permission errors:
- Ensure the backup directory is writable
- Check that you have permissions to access VirtualBox VMs
- On macOS, you may need to grant Terminal/iTerm full disk access in System Preferences > Security & Privacy > Privacy > Full Disk Access

### VM is Running / Disk Locked Error

If you encounter an error like `VBOX_E_INVALID_OBJECT_STATE` or "Medium is locked for writing", the VM is likely running. The script handles this automatically based on the `handle_running_vms` configuration:

- **Default behavior (`"pause"`)**: The script will automatically pause the VM, perform the backup, then resume it. This is the recommended setting as it preserves the VM's running state.
- **`"suspend"`**: Saves the VM state and suspends it before backup. The VM will remain suspended after backup.
- **`"skip"`**: Skips running VMs and logs a warning.
- **`"fail"`**: Fails the backup if a VM is running.

To change this behavior, edit `config.json` and set `handle_running_vms` to your preferred option.

### Disk Space

Monitor disk space regularly. Large VMs can consume significant disk space. Adjust `retention_days` or `backup_directory` to use external storage.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Disclaimer

This script is provided as-is. Always test backups and verify they can be restored before relying on them for production use. The authors are not responsible for any data loss.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

