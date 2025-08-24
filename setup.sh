#!/bin/bash

# TikTok Auto Uploader Setup Script
# This script sets up the complete environment for TikTokAutoUploader v2.1

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS and Linux distribution
detect_os() {
    case "$OSTYPE" in
        linux*)   OS="linux" ;;
        darwin*)  OS="macos" ;;
        msys*)    OS="windows" ;;
        cygwin*)  OS="windows" ;;
        *)        OS="unknown" ;;
    esac
}

# Function to detect Linux distribution
detect_linux_distro() {
    DISTRO="unknown"
    PACKAGE_MANAGER="unknown"
    
    # Check for os-release file (systemd standard)
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian)
                DISTRO="$ID"
                PACKAGE_MANAGER="apt"
                ;;
            fedora)
                DISTRO="fedora"
                PACKAGE_MANAGER="dnf"
                ;;
            centos|rhel|"rocky"*|"alma"*)
                DISTRO="centos"
                # Check if dnf is available, otherwise use yum
                if command_exists dnf; then
                    PACKAGE_MANAGER="dnf"
                else
                    PACKAGE_MANAGER="yum"
                fi
                ;;
            arch|manjaro|endeavouros)
                DISTRO="arch"
                PACKAGE_MANAGER="pacman"
                ;;
            *)
                # Check ID_LIKE for derivative distributions
                case "$ID_LIKE" in
                    *arch*)
                        DISTRO="arch"
                        PACKAGE_MANAGER="pacman"
                        ;;
                    *debian*)
                        DISTRO="debian"
                        PACKAGE_MANAGER="apt"
                        ;;
                    *fedora*)
                        DISTRO="fedora"
                        PACKAGE_MANAGER="dnf"
                        ;;
                    *rhel*)
                        DISTRO="centos"
                        if command_exists dnf; then
                            PACKAGE_MANAGER="dnf"
                        else
                            PACKAGE_MANAGER="yum"
                        fi
                        ;;
                esac
                ;;
        esac
    fi
    
    # Fallback detection methods
    if [ "$DISTRO" = "unknown" ]; then
        if [ -f /etc/debian_version ]; then
            DISTRO="debian"
            PACKAGE_MANAGER="apt"
        elif [ -f /etc/redhat-release ]; then
            if command_exists dnf; then
                DISTRO="fedora"
                PACKAGE_MANAGER="dnf"
            else
                DISTRO="centos"
                PACKAGE_MANAGER="yum"
            fi
        elif [ -f /etc/arch-release ]; then
            DISTRO="arch"
            PACKAGE_MANAGER="pacman"
        fi
    fi
    
    log_time "Detected Linux distribution: $DISTRO ($PACKAGE_MANAGER)"
}

# Package manager abstraction functions
install_packages_apt() {
    local packages="$@"
    print_status "Installing packages with apt: $packages"
    sudo apt-get update
    sudo apt-get install -y $packages
}

install_packages_dnf() {
    local packages="$@"
    print_status "Installing packages with dnf: $packages"
    sudo dnf install -y $packages
}

install_packages_yum() {
    local packages="$@"
    print_status "Installing packages with yum: $packages"
    sudo yum install -y $packages
}

install_packages_pacman() {
    local packages="$@"
    print_status "Installing packages with pacman: $packages"
    sudo pacman -Syu --noconfirm
    sudo pacman -S --noconfirm $packages
}

# Generic package installation function
install_packages() {
    local packages="$@"
    case "$PACKAGE_MANAGER" in
        apt)
            install_packages_apt $packages
            ;;
        dnf)
            install_packages_dnf $packages
            ;;
        yum)
            install_packages_yum $packages
            ;;
        pacman)
            install_packages_pacman $packages
            ;;
        *)
            print_error "Unsupported package manager: $PACKAGE_MANAGER"
            return 1
            ;;
    esac
}

# Function to get package names for different distros
get_package_name() {
    local package_type="$1"
    case "$package_type" in
        python3)
            case "$DISTRO" in
                ubuntu|debian) echo "python3 python3-pip python3-venv" ;;
                fedora|centos) echo "python3 python3-pip python3-venv" ;;
                arch) echo "python python-pip python-virtualenv" ;;
            esac
            ;;
        nodejs)
            case "$DISTRO" in
                ubuntu|debian) echo "nodejs npm" ;;
                fedora|centos) echo "nodejs npm" ;;
                arch) echo "nodejs npm" ;;
            esac
            ;;
        chromium)
            case "$DISTRO" in
                ubuntu|debian) echo "chromium-browser" ;;
                fedora) echo "chromium" ;;
                centos) echo "chromium" ;;
                arch) echo "chromium" ;;
            esac
            ;;
        aria2)
            case "$DISTRO" in
                ubuntu|debian|fedora|centos|arch) echo "aria2" ;;
            esac
            ;;
        ffmpeg)
            case "$DISTRO" in
                ubuntu|debian) echo "ffmpeg" ;;
                fedora) echo "ffmpeg" ;;
                centos) echo "ffmpeg" ;;  # Requires EPEL or RPM Fusion
                arch) echo "ffmpeg" ;;
            esac
            ;;
        build-tools)
            case "$DISTRO" in
                ubuntu|debian) echo "build-essential curl wget git" ;;
                fedora|centos) echo "gcc gcc-c++ make curl wget git" ;;
                arch) echo "base-devel curl wget git" ;;
            esac
            ;;
        *)
            echo "$package_type"  # Return as-is if no mapping found
            ;;
    esac
}

# Function to log with timestamp
log_time() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

# Function to check if running in a supported environment
check_environment() {
    if [ "$OS" = "linux" ] && [ "$DISTRO" = "unknown" ]; then
        print_error "Unsupported Linux distribution detected"
        print_warning "Supported distributions: Ubuntu, Debian, Fedora, CentOS/RHEL, Arch Linux"
        print_status "You can still try to run this script, but some packages may fail to install"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Header
echo "=========================================="
echo "   TikTok Auto Uploader Setup Script v2.1"
echo "=========================================="
echo ""

# Detect OS
detect_os
print_status "Detected OS: $OS"

# Detect Linux distribution if on Linux
if [ "$OS" = "linux" ]; then
    detect_linux_distro
fi

# Check if environment is supported
check_environment

# Check for root/sudo (optional for system tuning)
if [ "$EUID" -eq 0 ]; then 
   print_warning "Running as root. System optimizations will be applied."
   RUNNING_AS_ROOT=true
else
   print_status "Not running as root. System optimizations will be skipped."
   print_status "Run with sudo for system-level network optimizations."
   RUNNING_AS_ROOT=false
fi

# Step 1: Install UV (Python package manager)
print_status "Checking for UV..."
if ! command_exists uv; then
    print_status "Installing UV..."
    if [ "$OS" = "linux" ] || [ "$OS" = "macos" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    elif [ "$OS" = "windows" ]; then
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    fi
    
    if command_exists uv; then
        print_success "UV installed successfully"
    else
        print_error "Failed to install UV. Please install manually from https://github.com/astral-sh/uv"
        exit 1
    fi
else
    print_success "UV is already installed"
fi

# Step 2: Install Python 3.8+ if not present
print_status "Checking Python version..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
else
    print_status "Installing Python..."
    if [ "$OS" = "linux" ]; then
        PYTHON_PACKAGES=$(get_package_name python3)
        if [ -n "$PYTHON_PACKAGES" ]; then
            install_packages $PYTHON_PACKAGES
        else
            print_error "Python installation not supported for $DISTRO"
            print_warning "Please install Python manually from https://www.python.org/downloads/"
            exit 1
        fi
    elif [ "$OS" = "macos" ]; then
        brew install python3
    elif [ "$OS" = "windows" ]; then
        print_warning "Please install Python manually from https://www.python.org/downloads/"
        exit 1
    fi
fi

# Step 3: Create and activate virtual environment with UV
print_status "Setting up Python virtual environment with UV..."
if [ ! -d ".venv" ]; then
    uv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Step 4: Install Python requirements
print_status "Installing Python requirements..."
uv pip install -r requirements.txt
print_success "Python requirements installed"

# Function to install Node.js via nvm
install_nodejs_via_nvm() {
    print_status "Installing Node.js via nvm..."
    
    # Install nvm
    if ! command_exists nvm; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    fi
    
    # Install latest LTS Node.js
    if command_exists nvm; then
        nvm install --lts
        nvm use --lts
        nvm alias default lts/*
        print_success "Node.js installed via nvm"
        return 0
    else
        print_warning "nvm installation failed"
        return 1
    fi
}

# Step 5: Install Node.js if not present
print_status "Checking for Node.js..."
if ! command_exists node; then
    print_status "Installing Node.js..."
    
    # First try nvm for universal installation
    if install_nodejs_via_nvm; then
        print_success "Node.js installed successfully via nvm"
    elif [ "$OS" = "linux" ]; then
        # Fallback to distro packages
        print_status "nvm failed, trying distro packages..."
        NODEJS_PACKAGES=$(get_package_name nodejs)
        if [ -n "$NODEJS_PACKAGES" ]; then
            install_packages $NODEJS_PACKAGES
        else
            print_error "Node.js installation not supported for $DISTRO"
            print_warning "Please install Node.js manually from https://nodejs.org"
            exit 1
        fi
    elif [ "$OS" = "macos" ]; then
        if command_exists brew; then
            brew install node
        else
            print_error "Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [ "$OS" = "windows" ]; then
        print_warning "Please install Node.js manually from https://nodejs.org/en/download"
        exit 1
    fi
    
    # Verify installation
    if command_exists node; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION installed successfully"
    else
        print_error "Failed to install Node.js. Please install manually from https://nodejs.org"
        exit 1
    fi
else
    NODE_VERSION=$(node --version)
    print_success "Node.js $NODE_VERSION is already installed"
fi

# Step 6: Install npm packages for TikTok signature
print_status "Installing Node.js packages for TikTok signature..."
cd tiktok_uploader/tiktok-signature/
npm install
cd ../..
print_success "Node.js packages installed"

# Step 7: Install additional system dependencies
print_status "Installing additional system dependencies..."

if [ "$OS" = "linux" ]; then
    # Install build tools first
    print_status "Installing build tools..."
    BUILD_TOOLS=$(get_package_name build-tools)
    if [ -n "$BUILD_TOOLS" ]; then
        install_packages $BUILD_TOOLS
    fi
    
    # Install Chrome/Chromium for headless browser
    if ! command_exists google-chrome && ! command_exists chromium-browser && ! command_exists chromium; then
        print_status "Installing Chromium browser..."
        CHROMIUM_PACKAGES=$(get_package_name chromium)
        if [ -n "$CHROMIUM_PACKAGES" ]; then
            install_packages $CHROMIUM_PACKAGES
        fi
    fi
    
    # Install aria2c for faster downloads
    if ! command_exists aria2c; then
        print_status "Installing aria2c for optimized downloads..."
        ARIA2_PACKAGES=$(get_package_name aria2)
        if [ -n "$ARIA2_PACKAGES" ]; then
            install_packages $ARIA2_PACKAGES
        fi
    fi
    
    # Install ffmpeg for video processing
    if ! command_exists ffmpeg; then
        print_status "Installing ffmpeg..."
        FFMPEG_PACKAGES=$(get_package_name ffmpeg)
        if [ -n "$FFMPEG_PACKAGES" ]; then
            install_packages $FFMPEG_PACKAGES
        fi
    fi
    
    # Special handling for CentOS/RHEL - enable EPEL repository
    if [ "$DISTRO" = "centos" ]; then
        if ! rpm -q epel-release >/dev/null 2>&1; then
            print_status "Enabling EPEL repository for additional packages..."
            if [ "$PACKAGE_MANAGER" = "dnf" ]; then
                sudo dnf install -y epel-release
            else
                sudo yum install -y epel-release
            fi
        fi
        
        # Check for RPM Fusion for ffmpeg (optional)
        if ! rpm -q rpmfusion-free-release >/dev/null 2>&1; then
            print_status "Note: For ffmpeg on CentOS/RHEL, you may need RPM Fusion:"
            print_status "sudo dnf install --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm"
        fi
    fi
    
elif [ "$OS" = "macos" ]; then
    if command_exists brew; then
        # Install Chrome/Chromium
        if ! command_exists google-chrome && ! command_exists chromium; then
            print_status "Installing Chromium browser..."
            brew install --cask chromium
        fi
        
        # Install aria2c
        if ! command_exists aria2c; then
            print_status "Installing aria2c for optimized downloads..."
            brew install aria2
        fi
        
        # Install ffmpeg
        if ! command_exists ffmpeg; then
            print_status "Installing ffmpeg..."
            brew install ffmpeg
        fi
    else
        print_warning "Homebrew not found. Some dependencies may not be installed."
        print_status "Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
fi

# Step 8: Create required directories
print_status "Creating required directories..."
mkdir -p VideosDirPath
mkdir -p CookiesDir
print_success "Directories created"

# Step 9: Apply system optimizations (if running as root/sudo)
if [ "$RUNNING_AS_ROOT" = true ] && [ "$OS" = "linux" ]; then
    print_status "Applying system network optimizations..."
    
    # TCP buffer optimizations
    sysctl -w net.core.rmem_max=134217728 2>/dev/null || true
    sysctl -w net.core.wmem_max=134217728 2>/dev/null || true
    sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728" 2>/dev/null || true
    sysctl -w net.ipv4.tcp_wmem="4096 65536 134217728" 2>/dev/null || true
    
    # Enable BBR if available
    if modprobe tcp_bbr 2>/dev/null; then
        sysctl -w net.ipv4.tcp_congestion_control=bbr 2>/dev/null || true
        print_success "BBR congestion control enabled"
    fi
    
    print_success "System optimizations applied"
fi

# Step 10: Create activation script
print_status "Creating activation script..."
cat > activate.sh << 'EOF'
#!/bin/bash
# Activate the virtual environment
source .venv/bin/activate
echo "Virtual environment activated. You can now run:"
echo "  python cli.py login -n <username>"
echo "  python cli.py upload -u <username> -yt <youtube_url> -t <title> --fast --fast-net"
EOF
chmod +x activate.sh
print_success "Activation script created"

# Step 11: Test the installation
print_status "Testing installation..."
source .venv/bin/activate
python -c "import tiktok_uploader; print('✓ TikTok uploader module loads successfully')" 2>/dev/null || print_warning "Module import test failed"

# Final summary
echo ""
echo "=========================================="
echo "       Installation Complete! 🎉"
echo "=========================================="
echo ""
print_success "TikTok Auto Uploader has been successfully installed!"
if [ "$OS" = "linux" ]; then
    print_success "Multi-distribution support: $DISTRO ($PACKAGE_MANAGER)"
fi
echo ""
echo "Next steps:"
echo "1. Activate the environment: source activate.sh"
echo "2. Login to your account: python cli.py login -n <your_username>"
echo "3. Upload a video: python cli.py upload -u <username> -yt <youtube_url> -t \"Title\""
echo ""
echo "For fastest uploads, use these flags:"
echo "  --fast       Skip video processing"
echo "  --fast-net   Enable all network optimizations"
echo "  --dns auto   Auto-select fastest DNS"
echo ""
echo "To benchmark your network:"
echo "  python cli.py upload -u test -yt test -t test --benchmark"
echo ""
if [ "$RUNNING_AS_ROOT" = false ]; then
    print_warning "For maximum performance, run setup with sudo to apply system optimizations"
fi
echo ""
echo "Supported distributions:"
echo "  • Ubuntu/Debian (apt)"
echo "  • Fedora (dnf)" 
echo "  • CentOS/RHEL (yum/dnf)"
echo "  • Arch Linux (pacman)"
echo ""
print_success "Happy uploading! 🚀"