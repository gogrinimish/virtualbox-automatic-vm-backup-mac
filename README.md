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
git clone https://github.com/gogrinimish/virtualbox-automatic-vm-backup-mac.git
cd virtualbox-automatic-vm-backup-mac
```

2. Copy the example configuration file:
```bash
cp config.json.example config.json
```

3. Edit `config.json` to customize settings (see Configuration section)
   - **Important:** Set `vboxmanage_path` to an absolute path (e.g., `/usr/local/bin/VBoxManage`)
   - Use `which VBoxManage` to find the path on your system

4. Make the script executable:
```bash
chmod +x vbox_backup.py
```

5. Test your configuration:
```bash
python3 vbox_backup.py --validate
```
   This validates your config and tests VBoxManage access. See the [Testing](#testing) section for more details.

## Configuration

**Important:** A `config.json` file is required. The script will not run without it. Copy the example file and edit it:

```bash
cp config.json.example config.json
```

Then edit `config.json` to customize the backup behavior:

```json
{
    "backup_directory": "/path/to/backups",
    "retention_days": 30,
    "vms_to_backup": [],
    "vms_to_exclude": [],
    "compression": true,
    "include_manifest": true,
    "handle_running_vms": "suspend",
    "resume_after_backup": true,
    "auto_cleanup": true,
    "log_file": "backup.log",
    "log_level": "INFO",
    "vboxmanage_path": "/usr/local/bin/VBoxManage"
}
```

### Required Configuration Options

These keys **must** be present in your config file:

- **`backup_directory`**: Directory where backups will be stored (use absolute path)
- **`handle_running_vms`**: How to handle VMs that are running during backup
  - `"suspend"`: Save VM state and suspend, then backup (recommended - releases disk locks)
  - `"skip"`: Skip running VMs and log a warning
  - `"fail"`: Fail the backup if VM is running
- **`vboxmanage_path`**: **Absolute path** to VBoxManage command
  - **Important:** Use absolute path (e.g., `/usr/local/bin/VBoxManage` or `/Applications/VirtualBox.app/Contents/MacOS/VBoxManage`)
  - Launchd doesn't inherit your shell PATH, so relative paths won't work
  - Run `which VBoxManage` to find the path, or use the `--validate` option
- **`log_file`**: Path to log file (relative paths are resolved relative to script directory)

### Optional Configuration Options

- **`retention_days`**: Number of days to keep backups before automatic deletion (default: `30`)
- **`vms_to_backup`**: List of VM names to backup. Empty array `[]` means backup all VMs
  - Example: `["MyVM", "TestVM"]` - only backup these VMs
- **`vms_to_exclude`**: List of VM names to exclude from backup
  - Example: `["TemporaryVM"]` - backup all VMs except this one
- **`compression`**: Enable/disable compression of backups (default: `true`)
- **`include_manifest`**: Generate manifest file (.mf) with SHA-1 checksums for integrity verification (default: `true`)
  - Recommended for backups to detect corruption during restore
  - Manifest file is included in compressed backups
- **`resume_after_backup`**: Automatically resume VMs that were running before backup (default: `true`)
- **`auto_cleanup`**: Automatically clean up old backups after backup (default: `true`)
- **`log_level`**: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

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

## Testing

Before setting up automated backups, it's important to test your configuration to ensure everything works correctly, especially since launchd runs with a minimal PATH environment.

### Validate Configuration

Test your configuration without running a backup:
```bash
python3 vbox_backup.py --validate
```

This will:
- Verify the config file exists and is valid JSON
- Check that all required config keys are present
- Validate that VBoxManage path exists and is executable
- Test VBoxManage access by listing available VMs
- Display your backup directory and log file paths

### Test in Launchd-like Environment

Since launchd doesn't inherit your shell's PATH, test with a minimal PATH environment:
```bash
./test_launchd_env.sh
```

This script simulates launchd's environment and runs the validation. If validation passes here, the script should work correctly with launchd.

**Important:** If VBoxManage is in `/usr/local/bin` (common with Homebrew), you must use the absolute path in your config:
```json
{
  "vboxmanage_path": "/usr/local/bin/VBoxManage"
}
```

The validation will detect VBoxManage in common locations and suggest the correct absolute path if it's not found in PATH.

### Quick VM List Test

Quick test to verify VBoxManage access:
```bash
python3 vbox_backup.py --list-vms
```

This should list all your VirtualBox VMs if VBoxManage is configured correctly.

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

1. Copy the example plist file and edit it:
```bash
cp com.vboxbackup.plist.example ~/Library/LaunchAgents/com.vboxbackup.plist
```

Then edit `~/Library/LaunchAgents/com.vboxbackup.plist` and update the paths:

Example plist file:
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
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.vboxbackup.plist
```

3. To unload:
```bash
launchctl bootout gui/$(id -u)/com.vboxbackup
```

**Note:** On older macOS versions (before 10.11), you may need to use the deprecated commands:
- Load: `launchctl load ~/Library/LaunchAgents/com.vboxbackup.plist`
- Unload: `launchctl unload ~/Library/LaunchAgents/com.vboxbackup.plist`

4. Check service status:
```bash
launchctl list | grep com.vboxbackup
```

5. View logs:
```bash
tail -f /path/to/virtualbox-automatic-vm-backup-mac/launchd.log
tail -f /path/to/virtualbox-automatic-vm-backup-mac/launchd.error.log
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

### Config file not found

If you get an error that the config file doesn't exist:

1. Copy the example config file:
```bash
cp config.json.example config.json
```

2. Edit `config.json` and set all required keys (see [Configuration](#configuration) section)

3. Run validation to check your config:
```bash
python3 vbox_backup.py --validate
```

### VBoxManage not found

If you get an error that `VBoxManage` is not found:

1. Find VBoxManage on your system:
```bash
which VBoxManage
```

2. **Use absolute path in config.json** (required for launchd):
```json
{
    "vboxmanage_path": "/usr/local/bin/VBoxManage"
}
```

Common locations:
- `/usr/local/bin/VBoxManage` (Homebrew installation)
- `/Applications/VirtualBox.app/Contents/MacOS/VBoxManage` (App Store/standard installation)
- `/opt/homebrew/bin/VBoxManage` (Homebrew on Apple Silicon)

3. Test with launchd-like environment:
```bash
./test_launchd_env.sh
```

**Note:** Launchd doesn't inherit your shell PATH, so relative paths won't work. Always use absolute paths.

### Permission Errors

If you encounter permission errors:
- Ensure the backup directory is writable
- Check that you have permissions to access VirtualBox VMs
- On macOS, you may need to grant Terminal/iTerm full disk access in System Preferences > Security & Privacy > Privacy > Full Disk Access

### VM is Running / Disk Locked Error

If you encounter an error like `VBOX_E_INVALID_OBJECT_STATE` or "Medium is locked for writing", the VM is likely running. The script handles this automatically based on the `handle_running_vms` configuration:

- **`"suspend"`** (recommended): Saves the VM state and suspends it before backup, then automatically resumes it after backup completes
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

