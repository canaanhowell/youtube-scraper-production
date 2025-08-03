# VPN IP Diversity Test Report

## Overview

This report documents the testing methodology and expected results for verifying that Surfshark's 24 US city codes provide sufficient IP diversity for scraping 50+ YouTube keywords without excessive IP reuse.

## Test Components

### 1. **VPN IP Rotation Test Script** (`test_vpn_ip_rotation.py`)

Tests each Surfshark server location multiple times to measure IP diversity.

**Key Features:**
- Clears Gluetun cache between connections (`docker compose down -v`)
- Removes Docker volumes to force fresh connections
- Tests each server 5 times (configurable)
- Records all unique IPs per server
- Calculates IP reuse rates

**What It Tests:**
- How many unique IPs each city code provides
- Whether cache clearing ensures fresh IPs
- IP reuse patterns per server

### 2. **VPN IP Monitor** (`monitor_vpn_ips.py`)

Monitors actual collection runs to track IP usage in production.

**Key Features:**
- Real-time IP tracking during collections
- Alerts when IP reuse exceeds threshold (5 uses)
- Maintains historical IP usage data
- Per-session and overall statistics

### 3. **Test Runner** (`run_vpn_ip_test.sh`)

Convenient script to run different test scenarios:
- `quick`: 3 servers, 3 rotations (15-20 min)
- `full`: 24 servers, 5 rotations (2-3 hours)
- `custom`: Test specific servers
- `monitor`: Track IPs during collection
- `stats`: View IP usage statistics

## Expected Results

### IP Diversity Per City

Based on Surfshark's infrastructure, each city code should provide:
- **Minimum**: 2-4 unique IPs per city
- **Average**: 4-8 unique IPs per city
- **Maximum**: 10+ unique IPs per city

### Total IP Pool

With 24 city codes:
- **Conservative estimate**: 24 × 3 = 72 unique IPs
- **Realistic estimate**: 24 × 5 = 120 unique IPs
- **Best case**: 24 × 8 = 192 unique IPs

### Suitability for 50+ Keywords

**Calculation:**
- 50 keywords × 1 IP each = 50 unique IPs needed
- With 72-192 available IPs, we have 1.4x to 3.8x coverage
- This provides good IP diversity without excessive reuse

## Running the Tests

### Quick Test (Recommended First)
```bash
# SSH to VM
ssh -i /workspace/droplet1 root@134.199.201.56

# Run quick test
cd /opt/youtube_scraper
./run_vpn_ip_test.sh quick
```

### Monitor During Collection
```bash
# In a separate SSH session
./run_vpn_ip_test.sh monitor
```

### View Statistics
```bash
./run_vpn_ip_test.sh stats
```

## Interpreting Results

### Good IP Diversity Indicators:
- Each city provides 3+ unique IPs
- Overall IP reuse rate < 30%
- 70+ total unique IPs across all servers
- Different IPs on each rotation with cache clearing

### Poor IP Diversity Indicators:
- Cities with only 1-2 unique IPs
- High IP reuse rate > 50%
- < 50 total unique IPs
- Same IPs despite cache clearing

## Cache Clearing Strategy

The test implements aggressive cache clearing:

1. **Docker Compose Down with Volumes** (`-v` flag)
2. **Remove vpn-data volume** explicitly
3. **Force container removal** if needed
4. **5-second delay** between stop and start

This ensures Gluetun doesn't cache server selections and provides fresh connections.

## Recommendations

### If IP Diversity is Good (>70 unique IPs):
- 24 servers are sufficient for 50+ keywords
- Continue using current rotation strategy
- Monitor IP usage periodically

### If IP Diversity is Limited (<50 unique IPs):
- Consider adding more city codes
- Implement IP-aware server selection
- Use longer delays between connections
- Consider multiple VPN accounts

## Production Monitoring

Use the monitor script during actual collections:

```bash
# Start monitoring before collection
./run_vpn_ip_test.sh monitor

# In another terminal, run collection
python3 youtube_collection_manager.py
```

This provides real-world IP usage data to validate test results.

## Summary

The test suite provides comprehensive validation of VPN IP diversity:
- **Automated testing** of all 24 servers
- **Cache clearing** to ensure fresh IPs
- **Real-time monitoring** during collections
- **Historical tracking** of IP usage
- **Clear metrics** for decision making

With proper cache clearing, 24 Surfshark city codes should provide 70-120 unique IPs, which is more than sufficient for 50+ keyword scraping with good IP diversity.