#!/bin/bash

# Extract just the detection functions for testing
source <(head -n 220 setup.sh | tail -n +31)

echo "Testing distribution detection..."
echo "================================"

detect_os
echo "OS: $OS"

if [ "$OS" = "linux" ]; then
    detect_linux_distro
    echo "Distribution: $DISTRO"
    echo "Package Manager: $PACKAGE_MANAGER"
    
    echo
    echo "Testing package name mapping:"
    echo "Python3: $(get_package_name python3)"
    echo "Node.js: $(get_package_name nodejs)"
    echo "Chromium: $(get_package_name chromium)"
    echo "Build tools: $(get_package_name build-tools)"
fi