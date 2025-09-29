#!/bin/bash

# FragDropDetector Installer Script
# Simple installation helper for non-technical users
# Usage: bash install.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Header
echo "============================================"
echo "   FragDropDetector Installation Script"
echo "   Montagne Parfums Drop Monitor"
echo "============================================"
echo ""

# Check if running on Raspberry Pi or Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This script is designed for Linux/Raspberry Pi"
    exit 1
fi

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.11 or higher:"
    echo "  sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    print_warn "Python $PYTHON_VERSION detected. Python 3.11+ is recommended."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_info "Python $PYTHON_VERSION detected ✓"
fi

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the FragDropDetector directory"
    echo "Usage: cd FragDropDetector && bash install.sh"
    exit 1
fi

# Step 1: Install system dependencies
print_info "Installing system dependencies..."
if command -v apt &> /dev/null; then
    echo "This script needs to install some system packages."
    echo "Commands to run:"
    echo "  - python3-venv (for virtual environments)"
    echo "  - git (for version control)"
    echo ""
    read -p "Install required packages? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        sudo apt update
        sudo apt install -y python3-venv git
    fi
fi

# Step 2: Create virtual environment
print_info "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    print_warn "Virtual environment already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
    fi
else
    python3 -m venv venv
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Step 3: Install Python packages
print_info "Installing Python packages (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Install Playwright browser
print_info "Installing Chromium browser for web scraping..."
playwright install chromium
playwright install-deps chromium

# Step 5: Create default .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating configuration file..."
    cp .env.example .env
    print_warn ".env file created from template"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  IMPORTANT: Reddit API Setup Required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "You need to create a Reddit app to monitor r/MontagneParfums:"
    echo ""
    echo "1. Go to: https://www.reddit.com/prefs/apps"
    echo "2. Click 'Create App' or 'Create Another App'"
    echo "3. Fill in:"
    echo "   - Name: FragDropDetector"
    echo "   - Type: Select 'script'"
    echo "   - Redirect URI: http://localhost:8080"
    echo "4. Click 'Create app'"
    echo "5. Copy the Client ID (under 'personal use script')"
    echo "6. Copy the Secret"
    echo ""
    read -p "Press Enter when ready to add your Reddit credentials..."

    # Get Reddit credentials
    echo ""
    read -p "Enter Reddit Client ID: " CLIENT_ID
    read -p "Enter Reddit Client Secret: " CLIENT_SECRET
    read -p "Enter your Reddit username (without u/): " USERNAME

    # Update .env file
    sed -i "s/your_client_id_here/$CLIENT_ID/" .env
    sed -i "s/your_client_secret_here/$CLIENT_SECRET/" .env
    sed -i "s/YourUsername/$USERNAME/" .env

    print_info "Reddit credentials saved to .env"
else
    print_info ".env file already exists ✓"
fi

# Step 6: Test the configuration
print_info "Testing configuration..."
if python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); exit(0 if os.getenv('REDDIT_CLIENT_ID') and os.getenv('REDDIT_CLIENT_SECRET') else 1)" 2>/dev/null; then
    print_info "Reddit credentials configured ✓"
else
    print_warn "Reddit credentials not configured"
    echo "Edit .env file manually to add your Reddit API credentials"
fi

# Step 7: Reddit Authentication
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Reddit User Authentication"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To monitor r/MontagneParfums (including member-only posts),"
echo "you need to authenticate with Reddit."
echo ""
read -p "Set up Reddit authentication now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
        print_info "SSH session detected. You'll need to:"
        echo "1. Open a new terminal on your LOCAL computer"
        echo "2. Run: ssh -L 8080:localhost:8080 $(whoami)@$(hostname -I | awk '{print $1}')"
        echo "3. Keep that terminal open"
        echo ""
        read -p "Press Enter when the SSH tunnel is ready..."
    fi

    print_info "Starting authentication process..."
    python3 generate_token_headless.py
fi

# Step 8: Optional - Set up systemd services
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Auto-Start Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Would you like FragDropDetector to start automatically when your system boots?"
read -p "Install auto-start services? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Installing systemd services..."

    # Create service files with correct paths
    WORKING_DIR=$(pwd)
    USER=$(whoami)

    # Update service files with correct paths
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$WORKING_DIR|g" fragdrop.service
    sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $WORKING_DIR/main.py|g" fragdrop.service
    sed -i "s|User=.*|User=$USER|g" fragdrop.service

    if [ -f "fragdrop-web.service" ]; then
        sed -i "s|WorkingDirectory=.*|WorkingDirectory=$WORKING_DIR|g" fragdrop-web.service
        sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $WORKING_DIR/web_server.py|g" fragdrop-web.service
        sed -i "s|User=.*|User=$USER|g" fragdrop-web.service
    fi

    # Install services
    sudo cp fragdrop.service /etc/systemd/system/
    [ -f "fragdrop-web.service" ] && sudo cp fragdrop-web.service /etc/systemd/system/

    sudo systemctl daemon-reload
    sudo systemctl enable fragdrop
    [ -f "fragdrop-web.service" ] && sudo systemctl enable fragdrop-web

    read -p "Start services now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        sudo systemctl start fragdrop
        [ -f "fragdrop-web.service" ] && sudo systemctl start fragdrop-web
        sleep 2
        sudo systemctl status fragdrop --no-pager | head -10
    fi

    print_info "Services installed and enabled ✓"
fi

# Step 9: Final instructions
echo ""
echo "============================================"
echo "   Installation Complete!"
echo "============================================"
echo ""
echo "To start the monitor manually:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "To access the web interface:"
echo "  python web_server.py"
echo "  Open: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "To check service status:"
echo "  sudo systemctl status fragdrop"
echo ""
echo "For help and documentation:"
echo "  https://github.com/yourusername/FragDropDetector"
echo ""
print_info "Happy drop hunting!"