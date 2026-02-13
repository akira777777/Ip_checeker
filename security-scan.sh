# IP Checker Pro - Security Scanning and Compliance Scripts
# =========================================================

#!/bin/bash

# Security scanning script for IP Checker Pro
# Usage: ./security-scan.sh

set -e

echo "=== IP Checker Pro Security Scan ==="
echo "$(date)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check for security vulnerabilities
check_vulnerabilities() {
    echo "🔍 Checking for security vulnerabilities..."
    
    # Check Python dependencies for known vulnerabilities
    if command -v safety &> /dev/null; then
        echo "Checking Python packages with safety..."
        safety check --full-report || echo -e "${YELLOW}⚠️  Some vulnerabilities found${NC}"
    else
        echo -e "${YELLOW}⚠️  Safety not installed. Install with: pip install safety${NC}"
    fi
    
    # Check for outdated packages
    echo "Checking for outdated packages..."
    pip list --outdated || echo "No outdated packages found"
    
    echo -e "${GREEN}✅ Vulnerability check completed${NC}"
    echo
}

# Function to check file permissions
check_permissions() {
    echo "🔒 Checking file permissions..."
    
    # Check for world-writable files
    local writable_files=$(find . -type f -perm -002 2>/dev/null | wc -l)
    if [ $writable_files -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $writable_files world-writable files${NC}"
        find . -type f -perm -002 -ls 2>/dev/null | head -10
    else
        echo -e "${GREEN}✅ No world-writable files found${NC}"
    fi
    
    # Check for files with SUID/SGID bits
    local suid_files=$(find . -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null | wc -l)
    if [ $suid_files -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $suid_files files with SUID/SGID bits${NC}"
        find . -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null
    else
        echo -e "${GREEN}✅ No SUID/SGID files found${NC}"
    fi
    
    echo
}

# Function to check configuration security
check_config_security() {
    echo "⚙️  Checking configuration security..."
    
    # Check for hardcoded secrets
    echo "Scanning for potential secrets..."
    local secret_patterns=("password\s*=" "secret\s*=" "key\s*=" "token\s*=")
    local secrets_found=0
    
    for pattern in "${secret_patterns[@]}"; do
        if grep -r -i -E "$pattern" --exclude-dir=.git --exclude="*.pyc" . 2>/dev/null | grep -v "example" | grep -v "test" > /dev/null; then
            echo -e "${YELLOW}⚠️  Potential secret found matching pattern: $pattern${NC}"
            grep -r -i -E "$pattern" --exclude-dir=.git --exclude="*.pyc" . 2>/dev/null | grep -v "example" | grep -v "test" | head -5
            secrets_found=1
        fi
    done
    
    if [ $secrets_found -eq 0 ]; then
        echo -e "${GREEN}✅ No obvious secrets found in code${NC}"
    fi
    
    # Check .env file security
    if [ -f ".env" ]; then
        echo "Checking .env file permissions..."
        local env_perms=$(stat -c "%a" .env 2>/dev/null || echo "644")
        if [ "$env_perms" != "600" ]; then
            echo -e "${YELLOW}⚠️  .env file has permissions $env_perms, should be 600${NC}"
        else
            echo -e "${GREEN}✅ .env file has secure permissions${NC}"
        fi
    fi
    
    echo
}

# Function to check Docker security
check_docker_security() {
    echo "🐳 Checking Docker security..."
    
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠️  Docker not found${NC}"
        return
    fi
    
    # Check if running as root
    if docker ps --format "{{.Image}}" | grep -q "ip-checker"; then
        local user_check=$(docker inspect ip-checker-pro | grep -A2 "User" | grep "User" | cut -d'"' -f4)
        if [ "$user_check" = "root" ] || [ -z "$user_check" ]; then
            echo -e "${YELLOW}⚠️  Container may be running as root${NC}"
        else
            echo -e "${GREEN}✅ Container running as non-root user${NC}"
        fi
    fi
    
    # Check for privileged containers
    local privileged=$(docker inspect ip-checker-pro 2>/dev/null | grep -c "\"Privileged\": true" || echo "0")
    if [ $privileged -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Container running in privileged mode${NC}"
    else
        echo -e "${GREEN}✅ Container not running in privileged mode${NC}"
    fi
    
    echo
}

# Function to check network security
check_network_security() {
    echo "🌐 Checking network security..."
    
    # Check for exposed ports
    if command -v netstat &> /dev/null; then
        echo "Checking listening ports..."
        netstat -tlnp | grep ":5000\|:6379\|:5432" || echo "No unexpected ports found"
    fi
    
    # Check firewall status (Linux)
    if command -v ufw &> /dev/null; then
        local ufw_status=$(ufw status | head -1)
        echo "UFW status: $ufw_status"
    fi
    
    echo
}

# Function to generate security report
generate_report() {
    echo "📋 Generating security report..."
    
    local report_file="security-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "IP Checker Pro Security Report"
        echo "Generated: $(date)"
        echo "================================"
        echo
        echo "System Information:"
        uname -a
        echo
        echo "Python Version:"
        python --version
        echo
        echo "Docker Version:"
        docker --version 2>/dev/null || echo "Docker not installed"
        echo
        echo "Security Scan Results:"
        echo "---------------------"
        # Add scan results here
    } > "$report_file"
    
    echo -e "${GREEN}✅ Security report saved to $report_file${NC}"
}

# Function to run automated fixes
apply_fixes() {
    echo "🔧 Applying security fixes..."
    
    # Fix .env permissions
    if [ -f ".env" ]; then
        chmod 600 .env
        echo -e "${GREEN}✅ Fixed .env permissions${NC}"
    fi
    
    # Remove world-writable permissions
    find . -type f -perm -002 -exec chmod o-w {} \; 2>/dev/null
    echo -e "${GREEN}✅ Removed world-writable permissions${NC}"
    
    echo
}

# Main execution
main() {
    local run_fixes=false
    local generate_report_flag=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                run_fixes=true
                shift
                ;;
            --report)
                generate_report_flag=true
                shift
                ;;
            *)
                echo "Usage: $0 [--fix] [--report]"
                echo "  --fix    Apply automatic security fixes"
                echo "  --report Generate detailed security report"
                exit 1
                ;;
        esac
    done
    
    # Run all security checks
    check_vulnerabilities
    check_permissions
    check_config_security
    check_docker_security
    check_network_security
    
    # Apply fixes if requested
    if [ "$run_fixes" = true ]; then
        apply_fixes
    fi
    
    # Generate report if requested
    if [ "$generate_report_flag" = true ]; then
        generate_report
    fi
    
    echo "=== Security Scan Complete ==="
    echo -e "${GREEN}✅ Security scan finished. Review any warnings above.${NC}"
}

# Run main function
main "$@"