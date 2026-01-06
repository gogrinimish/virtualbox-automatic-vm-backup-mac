# Quick Start Guide

Get up and running with VirtualBox Automatic VM Backup in 5 minutes!

## Step 1: Setup

```bash
# Clone or download this repository
cd virtualbox-automatic-vm-backup-mac

# Copy the example configuration
cp config.json.example config.json

# Make the script executable
chmod +x vbox_backup.py
```

## Step 2: Configure (Optional)

Edit `config.json` if you want to customize:
- Backup location
- Which VMs to backup
- Retention period
- etc.

For most users, the defaults work fine!

## Step 3: Test

```bash
# List your VMs
python3 vbox_backup.py --list-vms

# Run a test backup
python3 vbox_backup.py
```

## Step 4: Automate (Optional)

### Option A: Using launchd (Recommended for macOS)

1. Edit `com.vboxbackup.plist.example`:
   - Replace `/PATH/TO/` with your actual path
   - Adjust the time (Hour/Minute) if needed

2. Copy to LaunchAgents:
```bash
cp com.vboxbackup.plist.example ~/Library/LaunchAgents/com.vboxbackup.plist
```

3. Edit the plist file with your actual paths:
```bash
nano ~/Library/LaunchAgents/com.vboxbackup.plist
```

4. Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.vboxbackup.plist
```

### Option B: Using cron

```bash
# Edit crontab
crontab -e

# Add this line (adjust path and time as needed):
0 2 * * * cd /path/to/virtualbox-automatic-vm-backup-mac && /usr/bin/python3 vbox_backup.py
```

## That's it!

Your VMs will now be automatically backed up. Check the `backups/` directory for your backup files.

## Troubleshooting

**Can't find VBoxManage?**
- Make sure VirtualBox is installed
- Try: `which VBoxManage`
- If not found, edit `config.json` and set `vboxmanage_path` to the full path

**Permission errors?**
- Make sure the backup directory is writable
- On macOS, grant Terminal full disk access in System Preferences

**Need help?**
- Check the full [README.md](README.md) for detailed documentation
- Open an issue on GitHub

