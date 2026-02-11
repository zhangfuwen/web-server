# Web Server Deployment Guide

## Overview

This document provides complete deployment instructions for the Web Server with GTD task management system. The deployment follows Linux FHS (Filesystem Hierarchy Standard) and includes systemd integration.

## File System Layout

After installation, the system will have the following structure:

```
/opt/web-server/           # Main application directory
├── bin/                   # Executables
│   └── web-server        # Main launcher script
├── lib/                   # Python modules
│   ├── web_server.py     # Main server module
│   └── gtd.py            # GTD module
├── etc/                   # Configuration
│   └── web-server.conf   # Main configuration
├── var/                   # Runtime data
│   ├── log/              # Application logs
│   └── run/              # PID files
├── share/                 # Static resources
│   └── static/           # Web static files
└── systemd/              # Service files
    └── web-server.service

# Web root and data directories
/var/www/html/            # Web server root directory
└── gtd/                  # GTD data directory
    └── tasks.md          # GTD tasks file

# Symlinks
/usr/local/bin/web-server → /opt/web-server/bin/web-server
/etc/web-server → /opt/web-server/etc/
/var/log/web-server → /opt/web-server/var/log/
```

## Prerequisites

- Linux system (tested on Ubuntu/Debian, CentOS/RHEL)
- Python 3.7+
- Root/sudo access

## Quick Deployment

### Option 1: Automated Installation (Recommended)

```bash
# 1. Clone or download the project
git clone https://github.com/zhangfuwen/web-server.git
cd web-server

# 2. Make install script executable
chmod +x install.sh

# 3. Run installation (as root)
sudo ./install.sh
```

### Option 2: Manual Installation

```bash
# 1. Create directories
sudo mkdir -p /opt/web-server/{bin,lib,etc,var/{data/gtd,log,run},share/static,systemd}
sudo mkdir -p /etc/web-server /var/log/web-server /var/lib/web-server

# 2. Copy files
sudo cp web-server-unified.py /opt/web-server/lib/web_server.py
sudo cp gtd.py /opt/web-server/lib/
sudo cp -r static/* /opt/web-server/share/static/

# 3. Create executable
sudo tee /opt/web-server/bin/web-server << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/opt/web-server/lib')
from web_server import main
if __name__ == '__main__':
    main()
EOF
sudo chmod +x /opt/web-server/bin/web-server

# 4. Create symlink
sudo ln -sf /opt/web-server/bin/web-server /usr/local/bin/web-server

# 5. Install dependencies
sudo pip3 install requests beautifulsoup4 psutil
```

## Configuration

### Main Configuration File

The main configuration file is located at `/etc/web-server/web-server.conf`:

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
static_dir = /opt/web-server/share/static
log_dir = /var/log/web-server
pid_file = /var/run/web-server.pid
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
sudo systemctl start web-server

# Stop the service
sudo systemctl stop web-server

# Restart the service
sudo systemctl restart web-server

# Check status
sudo systemctl status web-server

# Enable auto-start on boot
sudo systemctl enable web-server

# View logs
sudo journalctl -u web-server -f
```

### Manual Control

```bash
# Start manually (for debugging)
web-server

# Start with specific port
web-server 8080

# Start with hot reload (development)
web-server --reload 8080
```

## Data Management

### GTD Data Files

- Location: `/var/www/html/gtd/tasks.md`
- Format: Markdown with GTD categories
- Backup: This file contains all tasks and comments
- Note: Located in web root for easy access and backup

### Log Files

- Location: `/var/log/web-server/`
- Rotation: Managed by systemd/journald
- View logs: `sudo journalctl -u web-server`

### Static Files

- Location: `/opt/web-server/share/static/`
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
sudo tar -czf /backup/web-server-config-$(date +%Y%m%d).tar.gz /etc/web-server/

# Backup web root (optional)
sudo tar -czf /backup/web-root-$(date +%Y%m%d).tar.gz /var/www/html/
```

### Updates

```bash
# 1. Stop service
sudo systemctl stop web-server

# 2. Backup data
sudo cp /var/lib/web-server/gtd/tasks.md /tmp/tasks-backup.md

# 3. Update files
sudo cp new-web_server.py /opt/web-server/lib/web_server.py
sudo cp new-gtd.py /opt/web-server/lib/gtd.py

# 4. Restore data
sudo cp /tmp/tasks-backup.md /var/lib/web-server/gtd/tasks.md

# 5. Start service
sudo systemctl start web-server
```

### Monitoring

```bash
# Check service status
sudo systemctl status web-server

# Monitor logs
sudo journalctl -u web-server --since "1 hour ago"

# Check disk space
df -h /var/lib/web-server/

# Check memory usage
ps aux | grep web-server
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port
   sudo lsof -i :8080
   
   # Kill process or change port in config
   sudo nano /etc/web-server/web-server.conf
   ```

2. **Permission denied**
   ```bash
   # Fix permissions
   sudo chown -R webserver:webserver /opt/web-server /var/lib/web-server /var/log/web-server
   ```

3. **Python dependencies missing**
   ```bash
   sudo pip3 install requests beautifulsoup4 psutil
   ```

4. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u web-server -n 50
   
   # Test manually
   sudo -u webserver web-server
   ```

### Log Locations

- Systemd logs: `journalctl -u web-server`
- Application logs: `/var/log/web-server/` (if configured)
- Error logs: `journalctl -u web-server -p err`

## Uninstallation

```bash
# Run uninstall script
sudo ./uninstall.sh

# Or manually
sudo systemctl stop web-server
sudo systemctl disable web-server
sudo rm -f /etc/systemd/system/web-server.service
sudo rm -rf /opt/web-server /etc/web-server /var/log/web-server /var/lib/web-server
sudo rm -f /usr/local/bin/web-server
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
1. Check logs: `sudo journalctl -u web-server`
2. Test manually: `sudo -u webserver web-server`
3. Review configuration: `/etc/web-server/web-server.conf`

## License

This project is open source. See LICENSE file for details.