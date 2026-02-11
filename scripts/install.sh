#!/bin/bash
# Web Server Installation Script
# Usage: sudo ./install.sh

set -e

# Configuration
INSTALL_DIR="/opt/web-server"
CONFIG_DIR="/etc/web-server"
LOG_DIR="/var/log/web-server"
WEB_ROOT="/var/www/html"
GTD_DATA_DIR="/var/www/html/gtd"
USER="webserver"
GROUP="webserver"
PORT="8080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_info "Starting Web Server installation..."

# Create user and group if they don't exist
if ! id "$USER" &>/dev/null; then
    print_info "Creating user '$USER'..."
    useradd --system --no-create-home --shell /bin/false "$USER"
fi

if ! getent group "$GROUP" &>/dev/null; then
    print_info "Creating group '$GROUP'..."
    groupadd --system "$GROUP"
fi

# Create directory structure
print_info "Creating directory structure..."

mkdir -p "$INSTALL_DIR"/{bin,lib,etc,var/{log,run},share/{static/{css,js,images,gtd},doc},systemd}
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$WEB_ROOT"
mkdir -p "$GTD_DATA_DIR"

# Copy files
print_info "Copying files..."

# Copy Python files
cp web-server-unified.py "$INSTALL_DIR/lib/web_server.py"
cp gtd.py "$INSTALL_DIR/lib/"

# Copy static files
cp -r static/* "$INSTALL_DIR/share/static/"

# Copy GTD data
if [ -f "gtd/tasks.md" ]; then
    cp gtd/tasks.md "$GTD_DATA_DIR/"
else
    # Create default tasks file
    cat > "$GTD_DATA_DIR/tasks.md" << 'EOF'
# Projects
- [ ] Web Server Installation

# Next Actions
- [ ] Configure the server
- [ ] Test all features

# Waiting For
- [ ] User feedback

# Someday/Maybe
- [ ] Add authentication
- [ ] Add HTTPS support
EOF
fi

# Create main executable script
cat > "$INSTALL_DIR/bin/web-server" << 'EOF'
#!/usr/bin/env python3
import sys
import os

# Add lib directory to Python path
lib_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# Import and run the server
from web_server import main

if __name__ == '__main__':
    main()
EOF

chmod +x "$INSTALL_DIR/bin/web-server"

# Create systemd service file
cat > "$INSTALL_DIR/systemd/web-server.service" << EOF
[Unit]
Description=Web Server with GTD Task Management
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONPATH=$INSTALL_DIR/lib"
ExecStart=$INSTALL_DIR/bin/web-server
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=web-server
ProtectSystem=strict
ReadWritePaths=$WEB_ROOT $LOG_DIR
NoNewPrivileges=true
PrivateTmp=true

# Security hardening
CapabilityBoundingSet=
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6
RestrictNamespaces=true
RestrictRealtime=true
SystemCallArchitectures=native
SystemCallFilter=@system-service
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
EOF

# Create configuration file
cat > "$INSTALL_DIR/etc/web-server.conf" << EOF
# Web Server Configuration
# This file is read by the web server on startup

[server]
port = $PORT
host = 0.0.0.0
base_dir = $WEB_ROOT
log_level = INFO

[gtd]
data_dir = $GTD_DATA_DIR
tasks_file = $GTD_DATA_DIR/tasks.md

[paths]
static_dir = /opt/web-server/share/static
log_dir = /var/log/web-server
pid_file = /var/run/web-server.pid
EOF

# Create symlinks
print_info "Creating symlinks..."

ln -sf "$INSTALL_DIR/etc/web-server.conf" "$CONFIG_DIR/web-server.conf"
ln -sf "$INSTALL_DIR/bin/web-server" "/usr/local/bin/web-server"

# Set permissions
print_info "Setting permissions..."

chown -R "$USER:$GROUP" "$INSTALL_DIR"
chown -R "$USER:$GROUP" "$LOG_DIR"
chown -R "$USER:$GROUP" "$WEB_ROOT"
chmod 755 "$INSTALL_DIR/bin/web-server"
chmod 644 "$INSTALL_DIR/etc/web-server.conf"
chmod 755 "$GTD_DATA_DIR"
chmod 644 "$GTD_DATA_DIR/tasks.md"

# Install Python dependencies
print_info "Installing Python dependencies..."

if command -v pip3 &> /dev/null; then
    pip3 install requests beautifulsoup4 psutil
else
    print_warn "pip3 not found, attempting to install Python packages via system package manager..."
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3-requests python3-bs4 python3-psutil
    elif command -v yum &> /dev/null; then
        yum install -y python3-requests python3-beautifulsoup4 python3-psutil
    elif command -v dnf &> /dev/null; then
        dnf install -y python3-requests python3-beautifulsoup4 python3-psutil
    else
        print_error "Cannot install Python dependencies. Please install manually:"
        print_error "  pip3 install requests beautifulsoup4 psutil"
    fi
fi

# Install systemd service
print_info "Installing systemd service..."

if [ -d "/etc/systemd/system" ]; then
    cp "$INSTALL_DIR/systemd/web-server.service" "/etc/systemd/system/"
    systemctl daemon-reload
    systemctl enable web-server.service
    
    print_info "Starting web-server service..."
    systemctl start web-server.service
    
    # Check status
    if systemctl is-active --quiet web-server.service; then
        print_info "Service started successfully!"
    else
        print_warn "Service might have failed to start. Check status with: systemctl status web-server"
    fi
else
    print_warn "Systemd not found. Service file created at: $INSTALL_DIR/systemd/web-server.service"
    print_warn "Manual installation required for init systems other than systemd."
fi

print_info "Installation completed successfully!"
print_info ""
print_info "Next steps:"
print_info "1. Edit configuration: $CONFIG_DIR/web-server.conf"
print_info "2. Start the server: systemctl start web-server"
print_info "3. Enable auto-start: systemctl enable web-server"
print_info ""
print_info "Server will be available at: http://localhost:$PORT"
print_info "GTD interface: http://localhost:$PORT/gtd"