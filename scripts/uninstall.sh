#!/bin/bash
# Web Server Uninstallation Script
# Usage: sudo ./uninstall.sh

set -e

# Configuration
INSTALL_DIR="/opt/web-server"
CONFIG_DIR="/etc/web-server"
LOG_DIR="/var/log/web-server"
WEB_ROOT="/var/www/html"
GTD_DATA_DIR="/var/www/html/gtd"
USER="webserver"
GROUP="webserver"

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

print_info "Starting Web Server uninstallation..."

# Stop and disable service
if systemctl is-active --quiet web-server.service 2>/dev/null; then
    print_info "Stopping web-server service..."
    systemctl stop web-server.service
fi

if systemctl is-enabled --quiet web-server.service 2>/dev/null; then
    print_info "Disabling web-server service..."
    systemctl disable web-server.service
fi

# Remove systemd service file
if [ -f "/etc/systemd/system/web-server.service" ]; then
    print_info "Removing systemd service file..."
    rm -f "/etc/systemd/system/web-server.service"
    systemctl daemon-reload
fi

# Remove symlinks
print_info "Removing symlinks..."

if [ -L "/usr/local/bin/web-server" ]; then
    rm -f "/usr/local/bin/web-server"
fi

if [ -L "/etc/web-server" ]; then
    rm -f "/etc/web-server"
fi

# Remove directories (with confirmation)
print_warn "The following directories will be removed:"
echo "  $INSTALL_DIR"
echo "  $CONFIG_DIR"
echo "  $LOG_DIR"
echo "  $GTD_DATA_DIR (GTD data only, not entire web root)"
echo ""
read -p "Do you want to remove these directories? [y/N]: " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Removing directories..."
    
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
    fi
    
    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"
    fi
    
    # Only remove GTD data directory, not the entire web root
    if [ -d "$GTD_DATA_DIR" ]; then
        rm -rf "$GTD_DATA_DIR"
    fi
else
    print_info "Directories preserved. You can manually remove them later."
fi

# Remove user and group (if no other processes using them)
print_info "Checking if user and group can be removed..."

# Check if user exists and has no other processes
if id "$USER" &>/dev/null; then
    if ! pgrep -u "$USER" >/dev/null 2>&1; then
        read -p "Remove user '$USER'? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            userdel "$USER" 2>/dev/null || true
        fi
    else
        print_warn "User '$USER' still has running processes. Not removing."
    fi
fi

if getent group "$GROUP" &>/dev/null; then
    # Check if group has members
    if [ -z "$(getent group "$GROUP" | cut -d: -f4)" ]; then
        read -p "Remove group '$GROUP'? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            groupdel "$GROUP" 2>/dev/null || true
        fi
    else
        print_warn "Group '$GROUP' still has members. Not removing."
    fi
fi

print_info "Uninstallation completed!"
print_info ""
print_info "Note: Python packages installed via pip were not removed."
print_info "To remove them manually: pip3 uninstall requests beautifulsoup4 psutil"