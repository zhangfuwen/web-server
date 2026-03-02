# Molt Server Deployment Guide

## Overview

This document provides complete deployment instructions for the Molt Server with GTD task management system. The deployment follows Linux FHS (Filesystem Hierarchy Standard) and includes systemd integration.

## File System Layout

After installation, the system will have the following structure:

```
/opt/molt-server/           # Main application directory
├── bin/                   # Executables
│   └── molt-server        # Main launcher script
├── lib/                   # Python modules
│   ├── molt_server.py     # Main server module
│   └── gtd.py            # GTD module
├── etc/                   # Configuration
│   └── molt-server.conf   # Main configuration
├── var/                   # Runtime data
│   ├── log/              # Application logs
│   └── run/              # PID files
├── share/                 # Static resources
│   └── static/           # Web static files
└── systemd/              # Service files
    └── molt-server.service

# Web root and data directories
/var/www/html/            # Web server root directory
└── gtd/                  # GTD data directory
    └── tasks.md          # GTD tasks file

# Symlinks
/usr/local/bin/molt-server → /opt/molt-server/bin/molt-server
/etc/molt-server → /opt/molt-server/etc/
/var/log/molt-server → /opt/molt-server/var/log/
```

## Prerequisites

- Linux system (tested on Ubuntu/Debian, CentOS/RHEL)
- Python 3.7+
- Root/sudo access

## Quick Deployment

### Option 1: Automated Installation (Recommended)

```bash
# 1. Clone or download the project
git clone https://github.com/zhangfuwen/molt-server.git
cd molt-server

# 2. Make install script executable
chmod +x install.sh

# 3. Run installation (as root)
sudo ./install.sh
```

### Option 2: Manual Installation

```bash
# 1. Create directories
sudo mkdir -p /opt/molt-server/{bin,lib,etc,var/{data/gtd,log,run},share/static,systemd}
sudo mkdir -p /etc/molt-server /var/log/molt-server /var/lib/molt-server

# 2. Copy files
sudo cp molt-server-unified.py /opt/molt-server/lib/molt_server.py
sudo cp gtd.py /opt/molt-server/lib/
sudo cp -r static/* /opt/molt-server/share/static/

# 3. Create executable
sudo tee /opt/molt-server/bin/molt-server << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/opt/molt-server/lib')
from molt_server import main
if __name__ == '__main__':
    main()
EOF
sudo chmod +x /opt/molt-server/bin/molt-server

# 4. Create symlink
sudo ln -sf /opt/molt-server/bin/molt-server /usr/local/bin/molt-server

# 5. Install dependencies
sudo pip3 install requests beautifulsoup4 psutil
```

## Configuration

### Main Configuration File

The main configuration file is located at `/etc/molt-server/molt-server.conf`:

```ini
[server]
port = 8080
host = 0.0.0.0
base_dir = /var/www/html
log_level = INFO

[gtd]
data_dir = /var/www/html/gtd
tasks_file = /var/www/html/gtd/tasks.md

[paths]
static_dir = /opt/molt-server/share/static
log_dir = /var/log/molt-server
pid_file = /var/run/molt-server.pid
```

### Environment Variables

You can also configure via environment variables:

```bash
export WEB_SERVER_PORT=8080
export WEB_SERVER_BASE_DIR=/var/www/html
export WEB_SERVER_LOG_LEVEL=INFO
```

## Service Management

### Systemd Commands

```bash
# Start the service
sudo systemctl start molt-server

# Stop the service
sudo systemctl stop molt-server

# Restart the service
sudo systemctl restart molt-server

# Check status
sudo systemctl status molt-server

# Enable auto-start on boot
sudo systemctl enable molt-server

# View logs
sudo journalctl -u molt-server -f
```

### Manual Control

```bash
# Start manually (for debugging)
molt-server

# Start with specific port
molt-server 8080

# Start with hot reload (development)
molt-server --reload 8080
```

## Data Management

### GTD Data Files

- Location: `/var/www/html/gtd/tasks.md`
- Format: Markdown with GTD categories
- Backup: This file contains all tasks and comments
- Note: Located in web root for easy access and backup

### Log Files

- Location: `/var/log/molt-server/`
- Rotation: Managed by systemd/journald
- View logs: `sudo journalctl -u molt-server`

### Static Files

- Location: `/opt/molt-server/share/static/`
- Subdirectories:
  - `css/` - Stylesheets
  - `js/` - JavaScript files
  - `images/` - Images and icons
  - `gtd/` - GTD frontend files

## Security Considerations

### User and Permissions

The installation creates a dedicated user `webserver` with:
- No login shell (`/bin/false`)
- Limited privileges
- Owns only necessary directories

### Service Hardening

The systemd service includes security features:
- Private `/tmp`
- No new privileges
- Restricted system calls
- Memory protection
- Read-only `/usr`, `/boot`, `/etc`

### Network Security

1. **Firewall**: Configure firewall to allow only necessary ports
   ```bash
   sudo ufw allow 8080/tcp
   ```

2. **Reverse Proxy**: For production, use nginx/apache as reverse proxy
   ```nginx
   # nginx example
   location / {
       proxy_pass http://localhost:8080;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **HTTPS**: Use Let's Encrypt with reverse proxy

## Maintenance

### Backup

```bash
# Backup GTD data
sudo cp /var/www/html/gtd/tasks.md /backup/tasks-$(date +%Y%m%d).md

# Backup configuration
sudo tar -czf /backup/molt-server-config-$(date +%Y%m%d).tar.gz /etc/molt-server/

# Backup web root (optional)
sudo tar -czf /backup/web-root-$(date +%Y%m%d).tar.gz /var/www/html/
```

### Updates

```bash
# 1. Stop service
sudo systemctl stop molt-server

# 2. Backup data
sudo cp /var/lib/molt-server/gtd/tasks.md /tmp/tasks-backup.md

# 3. Update files
sudo cp new-molt_server.py /opt/molt-server/lib/molt_server.py
sudo cp new-gtd.py /opt/molt-server/lib/gtd.py

# 4. Restore data
sudo cp /tmp/tasks-backup.md /var/lib/molt-server/gtd/tasks.md

# 5. Start service
sudo systemctl start molt-server
```

### Monitoring

```bash
# Check service status
sudo systemctl status molt-server

# Monitor logs
sudo journalctl -u molt-server --since "1 hour ago"

# Check disk space
df -h /var/lib/molt-server/

# Check memory usage
ps aux | grep molt-server
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port
   sudo lsof -i :8080
   
   # Kill process or change port in config
   sudo nano /etc/molt-server/molt-server.conf
   ```

2. **Permission denied**
   ```bash
   # Fix permissions
   sudo chown -R webserver:webserver /opt/molt-server /var/lib/molt-server /var/log/molt-server
   ```

3. **Python dependencies missing**
   ```bash
   sudo pip3 install requests beautifulsoup4 psutil
   ```

4. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u molt-server -n 50
   
   # Test manually
   sudo -u webserver molt-server
   ```

### Log Locations

- Systemd logs: `journalctl -u molt-server`
- Application logs: `/var/log/molt-server/` (if configured)
- Error logs: `journalctl -u molt-server -p err`

## Uninstallation

```bash
# Run uninstall script
sudo ./uninstall.sh

# Or manually
sudo systemctl stop molt-server
sudo systemctl disable molt-server
sudo rm -f /etc/systemd/system/molt-server.service
sudo rm -rf /opt/molt-server /etc/molt-server /var/log/molt-server /var/lib/molt-server
sudo rm -f /usr/local/bin/molt-server
sudo userdel webserver 2>/dev/null || true
sudo groupdel webserver 2>/dev/null || true
```

## Production Checklist

- [ ] Configure firewall
- [ ] Set up reverse proxy (nginx/apache)
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Configure monitoring (Prometheus, Grafana)
- [ ] Set up backups
- [ ] Configure log rotation
- [ ] Set up alerting
- [ ] Test failover procedures

## Support

For issues and questions:
1. Check logs: `sudo journalctl -u molt-server`
2. Test manually: `sudo -u webserver molt-server`
3. Review configuration: `/etc/molt-server/molt-server.conf`

## License

This project is open source. See LICENSE file for details.