#!/bin/bash
# Run VPN IP diversity test with cache clearing

echo "VPN IP Diversity Test Runner"
echo "============================"
echo ""
echo "This script will test VPN IP diversity by connecting to each server multiple times"
echo "with cache clearing between connections to ensure fresh IPs."
echo ""

# Check if running on VM
if [[ ! -f "/opt/youtube_app/.env" ]]; then
    echo "ERROR: This script must be run on the VM at /opt/youtube_app"
    echo "SSH to VM first: ssh -i /workspace/droplet1 root@134.199.201.56"
    exit 1
fi

# Parse arguments
MODE=${1:-quick}

cd /opt/youtube_app

case $MODE in
    quick)
        echo "Running QUICK test (3 servers, 3 rotations each)..."
        echo "This will take approximately 15-20 minutes"
        python3 test_vpn_ip_rotation.py --quick
        ;;
    
    full)
        echo "Running FULL test (24 servers, 5 rotations each)..."
        echo "WARNING: This will take approximately 2-3 hours!"
        read -p "Are you sure you want to run the full test? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 test_vpn_ip_rotation.py
        else
            echo "Full test cancelled"
            exit 0
        fi
        ;;
    
    custom)
        echo "Custom test - specify servers and rotations"
        echo "Example: ./run_vpn_ip_test.sh custom us-nyc.prod.surfshark.com us-lax.prod.surfshark.com --rotations 3"
        shift
        python3 test_vpn_ip_rotation.py --servers "$@"
        ;;
    
    monitor)
        echo "Starting VPN IP monitoring..."
        echo "This will monitor IP usage during collection runs"
        echo "Press Ctrl+C to stop monitoring"
        python3 monitor_vpn_ips.py --session "manual_$(date +%Y%m%d_%H%M%S)"
        ;;
    
    stats)
        echo "VPN IP Usage Statistics:"
        python3 monitor_vpn_ips.py --stats
        ;;
    
    *)
        echo "Usage: $0 [quick|full|custom|monitor|stats]"
        echo ""
        echo "Options:"
        echo "  quick   - Test 3 servers with 3 rotations each (15-20 min)"
        echo "  full    - Test all 24 servers with 5 rotations each (2-3 hours)"
        echo "  custom  - Test specific servers (provide server names)"
        echo "  monitor - Monitor IP usage during collection runs"
        echo "  stats   - Show IP usage statistics"
        echo ""
        echo "Examples:"
        echo "  $0 quick"
        echo "  $0 custom us-nyc.prod.surfshark.com us-lax.prod.surfshark.com --rotations 3"
        echo "  $0 monitor"
        exit 1
        ;;
esac

echo ""
echo "Test complete. Check the log files for detailed results:"
echo "  - vpn_ip_rotation_test.log (test output)"
echo "  - vpn_ip_rotation_results_*.json (detailed results)"
echo "  - vpn_ip_monitor.log (monitoring output)"
echo "  - vpn_ip_usage.json (IP usage history)"