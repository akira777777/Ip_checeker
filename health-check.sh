# IP Checker Pro - Health Check and Monitoring Scripts
# ====================================================

#!/bin/bash

# Health check script for IP Checker Pro
# Usage: ./health-check.sh

set -e

SERVICE_NAME="ip-checker-pro"
HEALTH_ENDPOINT="http://localhost:5000/api/health"
MAX_RETRIES=3
RETRY_DELAY=5

echo "Checking $SERVICE_NAME health..."

# Function to check service health
check_health() {
    local attempt=1
    local response=""
    local http_code=""
    
    while [ $attempt -le $MAX_RETRIES ]; do
        echo "Attempt $attempt/$MAX_RETRIES..."
        
        # Make HTTP request and capture response
        response=$(curl -s -w "%{http_code}" $HEALTH_ENDPOINT 2>/dev/null)
        http_code="${response: -3}"
        
        if [ "$http_code" = "200" ]; then
            echo "✅ Service is healthy"
            echo "Response: ${response%???}"
            return 0
        else
            echo "⚠️  Health check failed (HTTP $http_code)"
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "❌ Service is unhealthy after $MAX_RETRIES attempts"
    return 1
}

# Function to check Docker containers
check_containers() {
    echo "Checking Docker containers..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found"
        return 1
    fi
    
    # Check if containers are running
    local containers=$(docker ps --filter "name=ip-checker" --format "{{.Names}}: {{.Status}}")
    
    if [ -z "$containers" ]; then
        echo "❌ No IP Checker containers found"
        return 1
    fi
    
    echo "Running containers:"
    echo "$containers"
    
    # Check container health
    local unhealthy=$(docker ps --filter "name=ip-checker" --filter "health=unhealthy" --format "{{.Names}}")
    if [ -n "$unhealthy" ]; then
        echo "❌ Unhealthy containers: $unhealthy"
        return 1
    fi
    
    echo "✅ All containers are healthy"
    return 0
}

# Function to check system resources
check_resources() {
    echo "Checking system resources..."
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    echo "CPU Usage: ${cpu_usage}%"
    
    # Memory usage
    local mem_info=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
    echo "Memory Usage: $mem_info"
    
    # Disk usage
    local disk_usage=$(df -h / | awk 'NR==2{print $5}')
    echo "Disk Usage: $disk_usage"
    
    # Check if resources are within acceptable limits
    local cpu_num=$(echo $cpu_usage | cut -d'.' -f1)
    local mem_num=$(echo $mem_info | cut -d'%' -f1 | cut -d'.' -f1)
    local disk_num=$(echo $disk_usage | cut -d'%' -f1)
    
    if [ $cpu_num -gt 80 ] || [ $mem_num -gt 85 ] || [ $disk_num -gt 90 ]; then
        echo "⚠️  Resource usage is high"
        return 1
    fi
    
    echo "✅ Resources are within acceptable limits"
    return 0
}

# Function to check logs for errors
check_logs() {
    echo "Checking application logs..."
    
    local log_file="./logs/app.log"
    if [ ! -f "$log_file" ]; then
        echo "⚠️  Log file not found: $log_file"
        return 0
    fi
    
    # Check for recent errors
    local error_count=$(tail -n 100 "$log_file" | grep -c "ERROR\|CRITICAL" || true)
    if [ $error_count -gt 0 ]; then
        echo "⚠️  Found $error_count recent errors in logs"
        tail -n 20 "$log_file" | grep "ERROR\|CRITICAL" | tail -n 5
        return 1
    fi
    
    echo "✅ No recent errors found in logs"
    return 0
}

# Function to restart service if needed
restart_service() {
    echo "Restarting service..."
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose restart ip-checker
        echo "✅ Service restarted via docker-compose"
    else
        echo "❌ docker-compose.yml not found"
        return 1
    fi
}

# Main execution
main() {
    echo "=== IP Checker Pro Health Check ==="
    echo "$(date)"
    echo
    
    local all_checks_passed=true
    
    # Run all checks
    if ! check_containers; then
        all_checks_passed=false
    fi
    
    echo
    
    if ! check_health; then
        all_checks_passed=false
    fi
    
    echo
    
    if ! check_resources; then
        all_checks_passed=false
    fi
    
    echo
    
    if ! check_logs; then
        all_checks_passed=false
    fi
    
    echo
    echo "=== Summary ==="
    
    if [ "$all_checks_passed" = true ]; then
        echo "✅ All health checks passed"
        exit 0
    else
        echo "❌ Some health checks failed"
        
        # Ask user if they want to restart
        read -p "Do you want to restart the service? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            restart_service
        fi
        
        exit 1
    fi
}

# Run main function
main "$@"